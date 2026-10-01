import asyncio
import json
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from fastapi.testclient import TestClient

SLEIPNIR = Path(__file__).resolve().parents[2] / "Sleipnir"
sys.path[:0] = [str(SLEIPNIR / "src"), str(SLEIPNIR / "services/web_search/src")]
from web_search_service.main import create_app
from web_search_service.settings import Settings
from sleipnir_agent.tools.search import SearchResult
from sleipnir_agent.async_agent import AsyncAgent
from sleipnir_agent.client import Message, ToolCall
from sleipnir_agent.tools.registry import tool


def body(mode="search_first"):
    return {
        "run_id": "run_test", "agent_version": "0.1.0",
        "model_ref": {"source": "local", "id": "test"}, "execution_mode": mode,
        "messages": [{"role": "user", "content": "What changed?"}],
    }


class Backend:
    async def search(self, query, max_results=3):
        return [SearchResult(title="Reference", url="https://example.com", content="Reference content.")]


def response(request):
    stream = (
        'event: started\ndata: {"type":"started","run_id":"run_test","sequence":1}\n\n'
        'event: content_delta\ndata: {"type":"content_delta","run_id":"run_test","content":"Answer [source](https://example.com)"}\n\n'
        'event: completed\ndata: {"type":"completed","run_id":"run_test","finish_reason":"stop",'
        '"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\n'
    )
    return httpx.Response(200, text=stream)


class ServiceTests(unittest.TestCase):
    def test_search_answer_sources_auth_and_duplicate_run(self):
        settings = Settings(service_token="service", tavily_api_key="test-key")
        http = httpx.AsyncClient(transport=httpx.MockTransport(response))
        app = create_app(settings, http, Backend())
        headers = {"Authorization": "Bearer service", "X-Execution-Token": "token"}
        try:
            with TestClient(app) as client:
                self.assertEqual(client.post("/v1/runs", json=body()).status_code, 401)
                result = client.post("/v1/runs", json=body(), headers=headers)
                self.assertEqual(result.status_code, 200, result.text)
                events = [json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")]
                self.assertEqual(events[0]["type"], "started")
                self.assertEqual(events[-1]["type"], "completed")
                self.assertTrue(any(e["type"] == "sources" for e in events))
                self.assertTrue(any(e["type"] == "text_delta" for e in events))
                self.assertEqual([e["sequence"] for e in events], list(range(1, len(events)+1)))
                self.assertEqual(client.post("/v1/runs", json=body(), headers=headers).status_code, 409)
        finally:
            asyncio.run(http.aclose())

    def test_cancellation_stops_running_search(self):
        entered = threading.Event()
        class BlockingBackend:
            async def search(self, *args, **kwargs):
                entered.set()
                await asyncio.sleep(30)
        http = httpx.AsyncClient(transport=httpx.MockTransport(response))
        app = create_app(Settings(service_token="service", tavily_api_key="key"), http, BlockingBackend())
        headers = {"Authorization": "Bearer service", "X-Execution-Token": "token"}
        try:
            with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.post, "/v1/runs", json=body(), headers=headers)
                self.assertTrue(entered.wait(5))
                cancelled = client.post("/v1/runs/run_test/cancel", headers=headers)
                self.assertEqual(cancelled.json()["status"], "cancel_requested")
                result = future.result(timeout=5)
                events = [json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")]
                self.assertEqual(events[-1]["type"], "cancelled")
                self.assertEqual(sum(e["type"] in {"completed", "failed", "cancelled"} for e in events), 1)
        finally:
            asyncio.run(http.aclose())

    def test_tool_calling_search_then_final_stream(self):
        calls = []
        def gateway(request):
            payload = json.loads(request.content)
            calls.append(payload)
            if request.url.path.endswith("/stream"):
                return response(request)
            tool_results = [m for m in payload["messages"] if m["role"] == "tool"]
            message = {"role": "assistant", "content": "Ready"}
            if not tool_results:
                message = {"role": "assistant", "tool_calls": [{
                    "id": "search-1", "name": "web_search",
                    "arguments": json.dumps({"query": "current changes", "max_results": 2}),
                }]}
            return httpx.Response(200, json={
                "message": message, "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            })
        http = httpx.AsyncClient(transport=httpx.MockTransport(gateway))
        app = create_app(Settings(service_token="service", tavily_api_key="key"), http, Backend())
        try:
            with TestClient(app) as client:
                result = client.post("/v1/runs", json=body("tool_calling"),
                                     headers={"Authorization": "Bearer service", "X-Execution-Token": "token"})
                events = [json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")]
                self.assertEqual(events[-1]["type"], "completed", events)
                self.assertEqual(events[-1]["total_usage"]["total_tokens"], 9)
                self.assertTrue(any(e["type"] == "sources" for e in events))
                self.assertEqual(len(calls), 3)
                self.assertTrue(any(m["role"] == "tool" for m in calls[-1]["messages"]))
        finally:
            asyncio.run(http.aclose())

    def test_contract_copies_match_hub(self):
        hub = Path(__file__).resolve().parents[1]
        for name in ("execution_request.py", "execution_events.py"):
            self.assertEqual(
                (hub / "app/modules/agent_execution/schemas" / name).read_text(encoding="utf-8"),
                (SLEIPNIR / "services/web_search/src/web_search_service/contracts" / name).read_text(encoding="utf-8"),
            )


class ServiceAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_extra_tool_calls_get_results_without_losing_state(self):
        executed = []
        @tool
        async def search(query: str):
            executed.append(query)
            return "result"
        class Client:
            count = 0
            async def chat_completion(self, **kwargs):
                self.count += 1
                if self.count == 1:
                    return Message(role="assistant", provider_data="state", tool_calls=[
                        ToolCall(id=f"c{i}", name="search", arguments=json.dumps({"query": str(i)}))
                        for i in range(3)
                    ])
                history = kwargs["messages"]
                self.captured = history
                return Message(role="assistant", content="ready")
            async def chat_completion_stream(self, **kwargs):
                yield "answer"
        client = Client()
        agent = AsyncAgent(client, "model", tools=[search], max_tool_calls_per_iteration=1)
        _ = [event async for event in agent.run_messages_stream([Message(role="user", content="search")])]
        self.assertEqual(executed, ["0"])
        assistant = next(message for message in client.captured if message.tool_calls)
        self.assertEqual(len(assistant.tool_calls), 3)
        self.assertEqual(assistant.provider_data, "state")
        self.assertEqual(len([message for message in client.captured if message.role == "tool"]), 3)


if __name__ == "__main__":
    unittest.main()
