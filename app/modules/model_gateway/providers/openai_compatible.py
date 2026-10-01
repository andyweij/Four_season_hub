import json
from app.infrastructure.streaming.sse import read_sse


def message_to_wire(message):
    result = {"role": message.role}
    if message.content is not None or message.tool_calls:
        result["content"] = message.content
    if message.tool_calls:
        result["tool_calls"] = [
            {"id": t.id, "type": "function", "function": {"name": t.name, "arguments": t.arguments}}
            for t in message.tool_calls
        ]
    if message.tool_call_id:
        result["tool_call_id"] = message.tool_call_id
    return result


def build_payload(target, request, stream=False):
    payload = {
        "model": target.model_name, "messages": [message_to_wire(m) for m in request.messages],
        "stream": stream, **request.parameters.model_dump(exclude_none=True),
    }
    if request.tools:
        payload["tools"] = [
            {"type": "function", "function": t.model_dump()} for t in request.tools
        ]
        payload["tool_choice"] = request.tool_choice
    if stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


class OpenAICompatibleProvider:
    def __init__(self, http_client):
        self.http = http_client

    async def complete(self, target, request, api_key):
        response = await self.http.post(
            f"{target.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key or 'EMPTY'}"},
            json=build_payload(target, request), timeout=120,
        )
        if response.is_error:
            raise ValueError(f"Model provider rejected request (HTTP {response.status_code}).")
        data = response.json()
        if not data.get("choices"):
            raise ValueError("Model provider returned no choices.")
        choice = data["choices"][0]
        wire = choice["message"]
        return {
            "message": {
                "role": "assistant", "content": wire.get("content") or "",
                "tool_calls": [
                    {"id": t["id"], "name": t["function"]["name"], "arguments": t["function"]["arguments"]}
                    for t in wire.get("tool_calls", [])
                ],
            },
            "reasoning_content": wire.get("reasoning_content"),
            "finish_reason": choice.get("finish_reason"), "usage": data.get("usage"),
        }

    async def stream(self, target, request, api_key):
        finished = False
        usage = None
        async with self.http.stream(
            "POST", f"{target.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key or 'EMPTY'}"},
            json=build_payload(target, request, True), timeout=120,
        ) as response:
            if response.is_error:
                raise ValueError(f"Model provider rejected request (HTTP {response.status_code}).")
            async for _, text in read_sse(response.aiter_lines()):
                if text == "[DONE]":
                    if not finished:
                        raise ValueError("Model ended without a finish reason.")
                    break
                data = json.loads(text)
                if data.get("usage") is not None:
                    usage = data["usage"]
                choices = data.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                if delta.get("tool_calls"):
                    raise ValueError("Tool calls are not supported on the text-stream endpoint.")
                if delta.get("content"):
                    yield {"type": "content_delta", "content": delta["content"]}
                if delta.get("reasoning_content"):
                    yield {"type": "reasoning_delta", "content": delta["reasoning_content"]}
                if choice.get("finish_reason"):
                    finished = True
                    finish_reason = choice["finish_reason"]
        if not finished:
            raise ValueError("Model stream disconnected before completion.")
        yield {"type": "completed", "finish_reason": finish_reason, "usage": usage}
