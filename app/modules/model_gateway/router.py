import asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.infrastructure.streaming.sse import encode_sse
from app.modules.model_gateway.schemas.completion_request import CompletionRequest
from app.modules.model_gateway.schemas.completion_event import CompletionFailedEvent

router = APIRouter(prefix="/internal/v1/model", tags=["Internal model gateway"])


def bearer(request):
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Missing bearer token.")
    return token


async def authorized(request, body):
    try:
        return await request.app.state.agent_services.access_keys.verify_run_token(bearer(request), body)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc


@router.post("/completions")
async def complete(body: CompletionRequest, request: Request):
    remaining = await authorized(request, body)
    try:
        async with asyncio.timeout(remaining):
            return await request.app.state.agent_services.gateway.complete(body)
    except TimeoutError as exc:
        raise HTTPException(504, "Execution deadline exceeded.") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/completions/stream")
async def stream(body: CompletionRequest, request: Request):
    remaining = await authorized(request, body)
    gateway = request.app.state.agent_services.gateway
    try:
        await gateway.prepare(body, True)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    async def events():
        completion_id, sequence = "unstarted", 0
        try:
            async with asyncio.timeout(remaining):
                async for event in gateway.stream(body):
                    completion_id, sequence = event.completion_id, event.sequence
                    yield encode_sse(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            yield encode_sse(CompletionFailedEvent(
                run_id=body.run_id, completion_id=completion_id, sequence=sequence + 1,
                code="model_call_failed", message="Model request failed or timed out.",
            ))
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
