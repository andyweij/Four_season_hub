import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from urllib.parse import quote
from app.infrastructure.streaming.sse import read_sse


def fingerprint(message):
    data = message.model_dump(exclude={"provider_state_ref"})
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class GeminiProvider:
    """REST adapter; raw model Content preserves thought signatures."""
    def __init__(self, http_client, database):
        self.http = http_client
        self.states = database["model_provider_states"]

    async def ensure_indexes(self):
        await self.states.create_index("expires_at", expireAfterSeconds=0)

    async def payload(self, target, request):
        contents, systems, calls = [], [], {}
        for message in request.messages:
            if message.role == "system":
                systems.append(message.content)
                continue
            if message.role == "assistant" and message.provider_state_ref:
                state = await self.states.find_one({
                    "_id": message.provider_state_ref, "run_id": request.run_id,
                    "model_id": target.id, "source": target.source,
                    "fingerprint": fingerprint(message),
                    "expires_at": {"$gt": datetime.now(UTC)},
                })
                if state is None:
                    raise ValueError("Provider state is invalid or expired.")
                contents.append(state["content"])
                calls.update({t.id: t.name for t in message.tool_calls})
                continue
            if message.role == "tool":
                name = calls.get(message.tool_call_id)
                if name is None:
                    raise ValueError("Tool result has no matching call.")
                part = {"functionResponse": {
                    "name": name, "id": message.tool_call_id,
                    "response": {"result": message.content},
                }}
                if contents and contents[-1]["role"] == "user" and "functionResponse" in contents[-1]["parts"][0]:
                    contents[-1]["parts"].append(part)
                else:
                    contents.append({"role": "user", "parts": [part]})
            elif message.tool_calls:
                # Gemini tool continuations require the preserved original Content.
                raise ValueError("Gemini tool history requires provider_state_ref.")
            else:
                contents.append({
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content or ""}],
                })
        parameters = request.parameters
        config = {}
        for source, dest in (("temperature", "temperature"), ("top_p", "topP"), ("max_tokens", "maxOutputTokens")):
            value = getattr(parameters, source)
            if value is not None:
                config[dest] = value
        if parameters.reasoning_effort is not None:
            raise ValueError("Gemini reasoning_effort mapping is not configured.")
        payload = {"contents": contents, "generationConfig": config}
        if systems:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(systems)}]}
        if request.tools:
            payload["tools"] = [{"functionDeclarations": [
                {"name": t.name, "description": t.description, "parametersJsonSchema": t.parameters}
                for t in request.tools
            ]}]
            mode = {"auto": "AUTO", "none": "NONE", "required": "ANY"}[request.tool_choice]
            payload["toolConfig"] = {"functionCallingConfig": {"mode": mode}}
        return payload

    def url(self, target, stream=False):
        method = "streamGenerateContent?alt=sse" if stream else "generateContent"
        model = quote(target.model_name.removeprefix("models/"), safe="")
        return f"{target.base_url.rstrip('/')}/models/{model}:{method}"

    @staticmethod
    def usage(data):
        usage = data.get("usageMetadata")
        if usage is None:
            return None
        return {
            "prompt_tokens": usage.get("promptTokenCount"),
            "completion_tokens": usage.get("candidatesTokenCount"),
            "total_tokens": usage.get("totalTokenCount"),
        }

    async def complete(self, target, request, api_key):
        response = await self.http.post(
            self.url(target), json=await self.payload(target, request),
            headers={"x-goog-api-key": api_key}, timeout=120,
        )
        if response.is_error:
            raise ValueError(f"Gemini rejected request (HTTP {response.status_code}).")
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates or not candidates[0].get("content"):
            raise ValueError("Gemini returned no answer.")
        candidate = candidates[0]
        content = candidate["content"]
        text, reasoning, calls = [], [], []
        for part in content.get("parts", []):
            if "text" in part:
                (reasoning if part.get("thought") else text).append(part["text"])
            if "functionCall" in part:
                call = part["functionCall"]
                call_id = call.get("id") or f"call_{uuid4().hex}"
                call["id"] = call_id
                calls.append({"id": call_id, "name": call["name"],
                              "arguments": json.dumps(call.get("args", {}))})
        from app.modules.model_gateway.schemas.completion_request import ModelMessage
        message = ModelMessage(role="assistant", content="".join(text), tool_calls=calls)
        if calls:
            state_id = uuid4().hex
            await self.states.insert_one({
                "_id": state_id, "run_id": request.run_id, "model_id": target.id,
                "source": target.source, "fingerprint": fingerprint(message),
                "content": content, "expires_at": datetime.now(UTC) + timedelta(minutes=15),
            })
            message.provider_state_ref = state_id
        return {"message": message.model_dump(), "reasoning_content": "".join(reasoning) or None,
                "finish_reason": "tool_calls" if calls else candidate.get("finishReason"),
                "usage": self.usage(data)}

    async def stream(self, target, request, api_key):
        finished, usage, finish_reason = False, None, None
        async with self.http.stream(
            "POST", self.url(target, True), json=await self.payload(target, request),
            headers={"x-goog-api-key": api_key}, timeout=120,
        ) as response:
            if response.is_error:
                raise ValueError(f"Gemini rejected request (HTTP {response.status_code}).")
            async for _, text in read_sse(response.aiter_lines()):
                data = json.loads(text)
                usage = self.usage(data) or usage
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if "functionCall" in part:
                            raise ValueError("Unexpected tool call in final answer.")
                        if part.get("text"):
                            yield {"type": "reasoning_delta" if part.get("thought") else "content_delta",
                                   "content": part["text"]}
                    if candidate.get("finishReason"):
                        finished = True
                        finish_reason = candidate["finishReason"]
        if not finished:
            raise ValueError("Gemini stream ended without completion.")
        yield {"type": "completed", "finish_reason": finish_reason, "usage": usage}
