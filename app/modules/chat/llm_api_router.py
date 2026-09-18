from app.modules.chat.schemas.chat_request import ChatRequest
from app.modules.chat.schemas import chat_response
from fastapi import APIRouter
from app.modules.chat.dependencies import ChatStreamServiceDependency, ChatModelServiceDependency, \
    ConversationServiceDependency
import logging
from fastapi.responses import StreamingResponse
from app.modules.chat.schemas.conversation_list import ConversationList
from fastapi import Path
from app.modules.chat.schemas.MessageResponse import MessageResponse
from app.modules.chat.domain.enums import ChatContentType

logger = logging.getLogger("app")
router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

DEV_USER_ID = "dev-user"


@router.post("/stream", response_model=chat_response.ChatResponse)
async def chat(request: ChatRequest, chat_stream_service: ChatStreamServiceDependency):
    """
    Chat with the model.

    - **model**: The model to use for the chat.
    - **message**: The message to send to the model.
    - **stream**: Whether to stream the response or not.
    - **parameters**: The generation parameters to use for the chat.
    """

    contents = list(map(lambda msg: msg.content, request.messages))
    logger.info("Received message: %s", contents)

    async def event_generator():
        async for event in chat_stream_service.chat_stream(request, DEV_USER_ID):
            yield f"event: {event.type.value}\ndata: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/models", response_model=list[str])
async def get_models(chat_model_service: ChatModelServiceDependency):
    """
    Get the list of available models.
    """
    return await chat_model_service.get_models()


@router.get("/conversations", response_model=list[ConversationList])
async def get_conversations(conversation_service: ConversationServiceDependency):
    """
    Get the list of available conversations.
    """
    return [ConversationList(**conversation.model_dump()) for conversation in
            await conversation_service.get_conversation_list(DEV_USER_ID)]


@router.get("/sessions/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
        conversation_id: str = Path(..., min_length=24, max_length=24, description="對話的 ID"),
        conversation_service: ConversationServiceDependency = ...,
):
    """
    Get the list of messages in a conversation.
    """
    messages = await conversation_service.get_message_list(conversation_id, DEV_USER_ID)
    return [
        MessageResponse(
            role=message.role,
            content="".join(part.text for part in message.content if part.type == ChatContentType.TEXT),
        )
        for message in messages
    ]
