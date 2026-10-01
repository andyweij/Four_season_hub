import asyncio
import json
import time
from typing import Any, Literal
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from app.modules.model_gateway.router import bearer
from app.modules.model_gateway.schemas.completion_request import (
    CompletionRequest, ModelMessage, ToolDefinition,
)
from app.modules.model_gateway.providers.openai_compatible import message_to_wire

router = APIRouter(prefix="/model-api/v1", tags=["OpenAI-compatible model proxy"])


class ProxyCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    messages: list[dict[str, Any]] = Field(min_length=1)
    stream: bool = False
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: Literal["auto", "none", "required"] | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    stream_options: dict[str, Any] | None = None


async def proxy_key(request, count=True):
    try:
        return await request.app.state.agent_services.access_keys.authenticate_proxy(bearer(request), count)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(429, str(exc)) from exc


@router.get("/models")
async def models(request: Request):
    key = await proxy_key(request, False)
    return {"object": "list", "data": [
        {"id": alias, "object": "model", "created": 0, "owned_by": "four-season-hub"}
        for alias in key["models"]
    ]}


def convert(body, key):
    if body.model not in key["models"]:
        raise PermissionError("Model is not allowed by this proxy key.")
    if body.max_tokens is not None and body.max_completion_tokens is not None:
        raise ValueError("Specify only one output token limit.")
    messages = []
    for raw in body.messages:
        data = dict(raw)
        data.pop("name", None)
        if "tool_calls" in data:
            data["tool_calls"] = [
                {"id": t["id"], "name": t["function"]["name"], "arguments": t["function"]["arguments"]}
                for t in data["tool_calls"]
            ]
        messages.append(ModelMessage.model_validate(data))
    tools = []
    for item in body.tools:
        if item.get("type") != "function":
            raise ValueError("Only function tools are supported.")
        tools.append(ToolDefinition.model_validate(item["function"]))
    return CompletionRequest(
        run_id=f"proxy_{key['_id']}_{uuid4().hex}", model_ref=key["models"][body.model],
        messages=messages, tools=tools, tool_choice=body.tool_choice or ("auto" if tools else "none"),
        parameters={
            "temperature": body.temperature, "top_p": body.top_p,
            "max_tokens": body.max_tokens if body.max_tokens is not None else body.max_completion_tokens,
            "reasoning_effort": body.reasoning_effort,
        },
    )


@router.post("/chat/completions")
async def completions(body: ProxyCompletion, request: Request):
    key = await proxy_key(request)
    gateway = request.app.state.agent_services.gateway
    try:
        completion = convert(body, key)
        target = await gateway.resolver.resolve(completion.model_ref)
        if target.provider == "gemini" and (completion.tools or any(m.tool_calls for m in completion.messages)):
            raise ValueError("Gemini tool continuations require the internal gateway contract.")
        await gateway.prepare(completion, stream=body.stream and not completion.tools)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, "Unsupported or invalid proxy request.") from exc

    if not body.stream:
        try:
            async with asyncio.timeout(120):
                result = await gateway.complete(completion)
        except Exception as exc:
            raise HTTPException(502, "Model provider request failed.") from exc
        return {
            "id": result.completion_id, "object": "chat.completion", "created": int(time.time()),
            "model": body.model, "choices": [{
                "index": 0, "message": message_to_wire(result.message),
                "finish_reason": result.finish_reason,
            }], "usage": result.usage.model_dump() if result.usage else None,
        }

    async def events():
        cid, created = f"chatcmpl_{uuid4().hex}", int(time.time())
        def chunk(delta, finish=None, usage=None, empty=False):
            data = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": body.model,
                    "choices": [] if empty else [{"index": 0, "delta": delta, "finish_reason": finish}]}
            if usage is not None:
                data["usage"] = usage
            return "data: " + json.dumps(data) + "\n\n"
        try:
            async with asyncio.timeout(120):
                yield chunk({"role": "assistant"})
                if completion.tools:
                    # Buffer tool decisions, then emit compatible chunks.
                    result = await gateway.complete(completion)
                    wire = message_to_wire(result.message)
                    wire.pop("role", None)
                    if wire.get("tool_calls"):
                        for index, call in enumerate(wire["tool_calls"]):
                            call["index"] = index
                    yield chunk(wire)
                    yield chunk({}, result.finish_reason)
                    usage = result.usage
                else:
                    usage = None
                    async for event in gateway.stream(completion):
                        if event.type == "content_delta":
                            yield chunk({"content": event.content})
                        elif event.type == "reasoning_delta":
                            yield chunk({"reasoning_content": event.content})
                        elif event.type == "completed":
                            yield chunk({}, event.finish_reason)
                            usage = event.usage
                if body.stream_options and body.stream_options.get("include_usage") and usage:
                    yield chunk({}, usage=usage.model_dump(), empty=True)
            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            yield 'data: {"error":{"message":"Model stream failed.","type":"upstream_error"}}\n\n'
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
