import asyncio
import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
from pydantic import ValidationError
from app.modules.agent_execution.schemas.execution_request import ModelRef
from app.modules.agent_execution.schemas.task_request import AgentTaskRequest
from app.modules.agent_execution.schemas.execution_events import StartedEvent, CompletedEvent, FailedEvent
from app.modules.agent_execution.services.task_policy import TaskPolicy
from app.modules.agent_execution.services.agent_run_service import AgentRunService
from app.modules.agent_execution.infrastructure.remote_agent_client import RemoteAgentExecutor
from app.modules.agent_management.repositories.json_agent_catalog import JsonAgentCatalogRepository
from app.modules.agent_management.services.agent_registry_service import AgentRegistryService
from app.modules.agent_management.exceptions import AgentDisabledError
from app.modules.model_gateway.domain.model_target import ModelTarget, ModelCapabilities
from app.modules.model_gateway.schemas.completion_request import CompletionRequest, ModelMessage
from app.modules.model_gateway.services.model_gateway_service import ModelGatewayService, validate_history
from app.modules.model_gateway.providers.openai_compatible import OpenAICompatibleProvider
from app.modules.model_gateway.providers.gemini import GeminiProvider
from app.modules.model_gateway.security.access_key_service import AccessKeyService
from app.modules.model_gateway.compatibility.openai_router import ProxyCompletion, convert
from app.infrastructure.streaming.sse import read_sse

ROOT = Path(__file__).resolve().parents[1]


async def definition():
    repository = JsonAgentCatalogRepository(ROOT / "resources/agents/agents.json")
    agent = await repository.get("web-search")
    agent.enabled = True
    return agent


def task(**overrides):
    data = dict(run_id="run_test", agent_id="web-search",
                messages=[{"role": "user", "content": "Hello"}],
                model_ref={"source": "local", "id": "test"})
    return AgentTaskRequest(**(data | overrides))


def completion(**overrides):
    data = dict(run_id="run_test", model_ref={"source": "local", "id": "test"},
                messages=[{"role": "user", "content": "Hello"}])
    return CompletionRequest(**(data | overrides))


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_returns_independent_copies(self):
        repo = JsonAgentCatalogRepository(ROOT / "resources/agents/agents.json")
        item = await repo.get("web-search")
        item.enabled = True
        self.assertFalse((await repo.get("web-search")).enabled)
        with self.assertRaises(AgentDisabledError):
            await AgentRegistryService(repo).get_executable_definition("web-search")

    async def test_policy_default_model_and_no_mutation(self):
        agent = await definition()
        agent.model_binding.default_model_ref = ModelRef(source="local", id="default")
        original = task(model_ref=None)
        result = TaskPolicy().prepare(agent, original)
        self.assertEqual(result.model_ref.id, "default")
        self.assertIsNone(original.model_ref)

    async def test_policy_fixed_model_rejects_override(self):
        agent = await definition()
        agent.model_binding.type = "hub_fixed"
        with self.assertRaisesRegex(ValueError, "per-run"):
            TaskPolicy().prepare(agent, task())

    async def test_policy_options_and_parameter_capability(self):
        agent = await definition()
        with self.assertRaises(ValidationError):
            TaskPolicy().prepare(agent, task(options={"endpoint": "http://example.com"}))
        agent.capabilities.generation_parameters = False
        with self.assertRaises(ValueError):
            TaskPolicy().prepare(agent, task(parameters={"temperature": 0.5}))

    async def test_multiline_sse(self):
        async def lines():
            for line in ["event: delta", 'data: {"type":', 'data: "delta"}', "", ": ping", ""]:
                yield line
        frames = [frame async for frame in read_sse(lines())]
        self.assertEqual(json.loads(frames[0][1]), {"type": "delta"})

    async def test_remote_wrong_run_and_incomplete_stream(self):
        agent = await definition()
        run_repo = SimpleNamespace(get=AsyncMock(return_value={
            "user_id": "user", "expires_at": datetime.now(UTC) + timedelta(seconds=120),
        }))
        access = SimpleNamespace(issue_run_token=lambda *args: "token")
        resolver = SimpleNamespace(resolve=AsyncMock(return_value=SimpleNamespace(
            capabilities=ModelCapabilities(streaming=True),
        )))
        for text in [
            'event: started\ndata: {"type":"started","run_id":"wrong","sequence":1}\n\n',
            'event: started\ndata: {"type":"started","run_id":"run_test","sequence":1}\n\n',
        ]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, text=text)
            )) as client:
                executor = RemoteAgentExecutor(client, run_repo, access, resolver, "service")
                with self.assertRaises(ValueError):
                    _ = [event async for event in executor.stream_run(agent, task())]

    async def test_run_service_stops_after_one_terminal_event(self):
        class Executor:
            async def stream_run(self, agent, request):
                yield StartedEvent(run_id=request.run_id, sequence=1)
                yield CompletedEvent(run_id=request.run_id, sequence=2)
                yield FailedEvent(run_id=request.run_id, sequence=3, code="bad", message="bad")
        repository = SimpleNamespace(
            update_active=AsyncMock(), get=AsyncMock(return_value={}), terminal=AsyncMock(),
        )
        service = AgentRunService(None, repository, None, {"hub_native": Executor()}, None, None, [])
        result = [event async for event in service.stream_prepared(await definition(), task())]
        self.assertEqual([event.type for event in result], ["started", "completed"])
        repository.terminal.assert_awaited_once()

    async def test_run_cancel_ownership(self):
        repo = SimpleNamespace(get=AsyncMock(return_value=None))
        service = AgentRunService(None, repo, None, {}, None, None, [])
        with self.assertRaises(LookupError):
            await service.cancel("run_other", "user")
        repo.get.assert_awaited_once_with("run_other", "user")


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def test_tool_history_matching(self):
        messages = [
            ModelMessage(role="user", content="Search"),
            ModelMessage(role="assistant", tool_calls=[{"id": "c1", "name": "search", "arguments": "{}"}]),
            ModelMessage(role="tool", content="result", tool_call_id="c1"),
        ]
        validate_history(messages)
        with self.assertRaises(ValueError):
            validate_history(messages[:-1])
        with self.assertRaises(ValueError):
            validate_history([messages[-1]])

    async def test_token_bound_to_run_and_model(self):
        repo = AsyncMock()
        repo.find_one.return_value = {"status": "running", "expires_at": datetime.now(UTC) + timedelta(seconds=60)}
        authority = AccessKeyService({"model_proxy_keys": AsyncMock(), "model_proxy_rates": AsyncMock(),
                                      "agent_runs": repo}, "s" * 40)
        request = completion()
        token = authority.issue_run_token("run_test", "user", request.model_ref,
                                         datetime.now(UTC) + timedelta(seconds=60))
        self.assertGreater(await authority.verify_run_token(token, request), 0)
        with self.assertRaises(PermissionError):
            await authority.verify_run_token(token, completion(model_ref={"source": "local", "id": "other"}))
        repo.find_one.return_value = {"status": "completed"}
        with self.assertRaises(PermissionError):
            await authority.verify_run_token(token, request)

    async def test_openai_stream_usage_after_finish(self):
        text = (
            'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            'data: {"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\n'
            'data: [DONE]\n\n'
        )
        target = ModelTarget("local", "test", "test", "openai_compatible", "http://model/v1",
                             ModelCapabilities(streaming=True))
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, text=text))) as client:
            events = [event async for event in OpenAICompatibleProvider(client).stream(target, completion(), None)]
        self.assertEqual(events[-1]["usage"]["total_tokens"], 3)

    async def test_incomplete_model_stream_rejected(self):
        target = ModelTarget("local", "test", "test", "openai_compatible", "http://model/v1", ModelCapabilities())
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(
            200, text='data: {"choices":[{"delta":{"content":"partial"},"finish_reason":null}]}\n\n'
        ))) as client:
            with self.assertRaises(ValueError):
                _ = [event async for event in OpenAICompatibleProvider(client).stream(target, completion(), None)]

    def test_proxy_model_allowlist_and_tool_conversion(self):
        key = {"_id": "key", "models": {"alias": {"source": "local", "id": "test"}}}
        body = ProxyCompletion(model="alias", messages=[{"role": "user", "content": "Hi"}],
                               tools=[{"type": "function", "function": {
                                   "name": "search", "description": "Search", "parameters": {"type": "object"},
                               }}])
        converted = convert(body, key)
        self.assertEqual(converted.model_ref.id, "test")
        self.assertEqual(converted.tool_choice, "auto")
        with self.assertRaises(PermissionError):
            convert(body.model_copy(update={"model": "other"}), key)

    async def test_gemini_state_retains_signature_and_binds_history(self):
        collection = AsyncMock()
        payload = {"candidates": [{"content": {"role": "model", "parts": [
            {"functionCall": {"name": "search", "args": {"query": "hi"}}, "thoughtSignature": "signature"},
        ]}, "finishReason": "STOP"}]}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))) as client:
            provider = GeminiProvider(client, {"model_provider_states": collection})
            target = ModelTarget("cloud", "gemini", "gemini-test", "gemini",
                                 "http://gemini/v1beta", ModelCapabilities(tool_calling=True))
            result = await provider.complete(target, completion(), "key")
            state = collection.insert_one.call_args.args[0]
            self.assertEqual(state["content"]["parts"][0]["thoughtSignature"], "signature")
            collection.find_one.return_value = state
            assistant = ModelMessage.model_validate(result["message"])
            request = completion(messages=[
                {"role": "user", "content": "hi"}, assistant,
                {"role": "tool", "tool_call_id": assistant.tool_calls[0].id, "content": "result"},
            ])
            wire = await provider.payload(target, request)
            self.assertEqual(wire["contents"][1]["parts"][0]["thoughtSignature"], "signature")
            query = collection.find_one.call_args.args[0]
            self.assertEqual(query["run_id"], "run_test")
            collection.find_one.return_value = None
            with self.assertRaises(ValueError):
                await provider.payload(target, request)

    async def test_cloud_mapper_roundtrip(self):
        from app.modules.cloud_llm_management.infrastructure.persistence.postgres.mappers import to_domain, to_record
        from app.modules.cloud_llm_management.domain.cloud_llm import CloudLLM, Capabilities
        from app.modules.cloud_llm_management.domain.enums import CloudLLMProvider, CloudLLMStatus
        from app.modules.cloud_llm_management.domain.encrypted_credential import EncryptedCredential
        now = datetime.now(UTC)
        connection = CloudLLM(
            id="conn_test", name="test", provider=CloudLLMProvider.OPENAI_COMPATIBLE,
            model_name="test", base_url="http://model/v1", enabled=True,
            status=CloudLLMStatus.UNTESTED, max_model_len=8000,
            capabilities=Capabilities(False, True, False, False, True),
            api_key_hint="***", credential_configured=True, last_tested_at=None,
            last_latency_ms=None, created_by="user", created_at=now, updated_at=now,
        )
        result = to_domain(to_record(connection, EncryptedCredential(b"cipher", b"nonce", 1, "***")))
        self.assertTrue(result.supports_tool_calling)
        self.assertTrue(result.is_chat_model)




class ChatIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, cancelled=False):
        from app.modules.chat.services.chat_stream_service import ChatStreamService
        from app.modules.chat.schemas.chat_request import ChatRequest
        from app.modules.chat.domain.enums import MessageRole, MessageStatus
        from app.modules.agent_execution.schemas.execution_events import SourcesEvent, TextDeltaEvent, CancelledEvent
        question = SimpleNamespace(id="question", status=MessageStatus.COMPLETE, role=MessageRole.USER,
                                   content=[SimpleNamespace(text="Search this")])
        conversation = SimpleNamespace(id="conversation", model="test", agent_id="web-search")
        conversations = SimpleNamespace(
            create_conversation=AsyncMock(return_value=(conversation, question)),
            get_message_list=AsyncMock(return_value=[question]),
            add_assistant_message=AsyncMock(return_value=SimpleNamespace(id="answer")),
        )
        agent = await definition()
        async def prepare(request, user):
            self.assertEqual(user, "actual-user")
            return agent, request
        async def stream(agent, request):
            yield StartedEvent(run_id=request.run_id, sequence=1)
            yield SourcesEvent(run_id=request.run_id, sequence=2, sources=[
                {"id": "source1", "title": "Reference", "url": "https://example.com", "summary": "reference"}])
            yield TextDeltaEvent(run_id=request.run_id, sequence=3, content="partial answer")
            if cancelled:
                yield CancelledEvent(run_id=request.run_id, sequence=4)
            else:
                yield CompletedEvent(run_id=request.run_id, sequence=4, finish_reason="stop")
        agents = SimpleNamespace(runs=SimpleNamespace(prepare=prepare, stream_prepared=stream))
        service = ChatStreamService(None, conversations, None, agents)
        request = ChatRequest(modelRef={"source": "local", "id": "test"}, agentId="web-search",
                              messages=[{"role": "user", "content": [{"text": "Search this"}]}])
        events = [e async for e in service.chat_stream(request, "actual-user")]
        saved = conversations.add_assistant_message.await_args
        self.assertEqual(saved.args[1], "actual-user")
        self.assertEqual(saved.args[2].extract_text(), "partial answer")
        self.assertEqual(saved.kwargs["run_id"], events[0].run_id)
        self.assertEqual(saved.kwargs["agent_version"], agent.version)
        self.assertEqual(saved.kwargs["sources"][0]["url"], "https://example.com")
        return events, saved

    async def test_sources_and_run_metadata_are_persisted_before_done(self):
        events, saved = await self.exercise()
        self.assertEqual(events[-1].type, "done")
        self.assertEqual(saved.kwargs["status"], "complete")
        self.assertEqual(events[-1].assistant_message_id, "answer")

    async def test_cancelled_partial_answer_is_saved_without_done(self):
        events, saved = await self.exercise(cancelled=True)
        self.assertEqual(events[-1].type, "cancelled")
        self.assertEqual(saved.kwargs["status"], "cancelled")
        self.assertFalse(any(event.type == "done" for event in events))

if __name__ == "__main__":
    unittest.main()
