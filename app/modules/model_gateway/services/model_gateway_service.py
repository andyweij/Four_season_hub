from uuid import uuid4
from app.modules.model_gateway.schemas.completion_response import CompletionResponse
from app.modules.model_gateway.schemas.completion_event import (
    CompletionStartedEvent, ContentDeltaEvent, ReasoningDeltaEvent, CompletionCompletedEvent,
)


def normalize_usage(usage):
    if usage is None:
        return None
    return {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}


def validate_history(messages):
    pending, seen = set(), set()
    for message in messages:
        if message.role == "tool":
            if message.tool_call_id not in pending:
                raise ValueError("Tool result has no pending matching call.")
            pending.remove(message.tool_call_id)
            continue
        if pending:
            raise ValueError("Tool calls must have results before the next message.")
        for call in message.tool_calls:
            if call.id in seen:
                raise ValueError("Tool call IDs must be unique.")
            seen.add(call.id)
            pending.add(call.id)
    if pending:
        raise ValueError("Tool results are missing.")


class ModelGatewayService:
    def __init__(self, resolver, providers, cloud_repository, credential_cipher):
        self.resolver, self.providers = resolver, providers
        self.cloud, self.cipher = cloud_repository, credential_cipher

    async def prepare(self, request, stream=False):
        validate_history(request.messages)
        if sum(len(m.content or "") + sum(len(t.arguments) for t in m.tool_calls)
               for m in request.messages) > 500_000:
            raise ValueError("Model context exceeds gateway size limit.")
        target = await self.resolver.resolve(request.model_ref)
        if request.tools and request.tool_choice != "none" and not target.capabilities.tool_calling:
            raise ValueError("Model does not support tool calling.")
        if stream and (request.tools or request.tool_choice != "none"):
            raise ValueError("Text streaming does not accept tools.")
        if stream and not target.capabilities.streaming:
            raise ValueError("Model does not support streaming.")
        if request.parameters.reasoning_effort and not target.capabilities.reasoning_effort:
            raise ValueError("Model does not support reasoning_effort.")
        if (target.max_context_tokens and request.parameters.max_tokens
                and request.parameters.max_tokens > target.max_context_tokens):
            raise ValueError("Output limit exceeds model context.")
        key = None
        if target.credential_ref:
            credential = await self.cloud.get_credential(target.credential_ref)
            if credential is None:
                raise ValueError("Model credential is unavailable.")
            key = self.cipher.decrypt(credential)
        return target, self.providers[target.provider], key

    async def complete(self, request):
        target, provider, key = await self.prepare(request)
        data = await provider.complete(target, request, key)
        data["usage"] = normalize_usage(data.get("usage"))
        return CompletionResponse(run_id=request.run_id, completion_id=f"cmpl_{uuid4().hex}", **data)

    async def stream(self, request):
        target, provider, key = await self.prepare(request, True)
        completion_id, sequence = f"cmpl_{uuid4().hex}", 1
        yield CompletionStartedEvent(run_id=request.run_id, completion_id=completion_id, sequence=sequence)
        async for data in provider.stream(target, request, key):
            sequence += 1
            base = dict(run_id=request.run_id, completion_id=completion_id, sequence=sequence)
            if data["type"] == "content_delta":
                yield ContentDeltaEvent(**base, content=data["content"])
            elif data["type"] == "reasoning_delta":
                yield ReasoningDeltaEvent(**base, content=data["content"])
            elif data["type"] == "completed":
                yield CompletionCompletedEvent(**base, finish_reason=data.get("finish_reason"),
                                               usage=normalize_usage(data.get("usage")))
