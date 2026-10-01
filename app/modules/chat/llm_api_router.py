import asyncio
import logging
from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from app.modules.chat.schemas import ChatRequest, ConversationList, MessageResponse
from app.modules.chat.dependencies import (
    ChatStreamServiceDependency, ChatModelServiceDependency, ConversationServiceDependency,
)
from app.modules.chat.domain.enums import ChatContentType, ChatEventType
from app.modules.chat.domain.chat_stream_event import ChatStreamEvent
from app.security.dependencies import CurrentUserDependency
from app.infrastructure.streaming.sse import encode_sse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/stream")
async def chat(body: ChatRequest, chat_stream_service: ChatStreamServiceDependency,
               current_user: CurrentUserDependency):
    async def events():
        try:
            async for event in chat_stream_service.chat_stream(body, current_user.subject):
                yield encode_sse(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Chat execution failed", exc_info=False)
            yield encode_sse(ChatStreamEvent(type=ChatEventType.ERROR,
                                            content="Conversation or Agent request could not be completed."))
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/models", response_model=list[str])
async def get_models(chat_model_service: ChatModelServiceDependency, current_user: CurrentUserDependency):
    return await chat_model_service.get_models()


@router.get("/model-options")
async def model_options(request: Request, current_user: CurrentUserDependency):
    registry = request.app.state.model_registry_service
    options = [
        {"id": name, "source": "local", "name": name}
        for name in registry.get_all_running_instances()
        if registry.get_ready_chat_model(name) is not None
    ]
    cloud = request.app.state.cloud_llm_management_service
    for connection in await cloud.get_cloud_llm_list():
        if connection.enabled and connection.is_chat_model:
            options.append({"id": connection.id, "source": "cloud", "name": connection.name})
    return options


@router.get("/conversations", response_model=list[ConversationList])
async def conversations(conversation_service: ConversationServiceDependency, current_user: CurrentUserDependency):
    return [ConversationList(**c.model_dump()) for c in await conversation_service.get_conversation_list(current_user.subject)]


@router.get("/sessions/{conversation_id}/messages", response_model=list[MessageResponse])
async def messages(conversation_service: ConversationServiceDependency, current_user: CurrentUserDependency,
                   conversation_id: str = Path(..., min_length=24, max_length=24)):
    try:
        await conversation_service.get_conversation_by_id(conversation_id, current_user.subject)
        history = await conversation_service.get_message_list(conversation_id, current_user.subject)
    except ValueError as exc:
        raise HTTPException(404, "Conversation was not found.") from exc
    return [
        MessageResponse(
            role=m.role, content="".join(p.text for p in m.content if p.type == ChatContentType.TEXT),
            sources=m.sources, run_id=m.run_id, agent_id=m.agent_id,
            agent_version=m.agent_version, status=m.status,
        ) for m in history
    ]
