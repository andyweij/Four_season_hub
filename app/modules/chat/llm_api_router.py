import uuid

from app.modules.chat.schemas.chat_request import ChatRequest
from app.modules.chat.schemas import chat_response
from fastapi import APIRouter
from app.modules.chat.services.chat_stream_service import ChatStreamService
from app.modules.chat.dependencies import ChatStreamServiceDependency
import logging
from fastapi.responses import StreamingResponse

logger = logging.getLogger("app")
router = APIRouter(
    tags=["Chat"],
)

DEV_USER_ID = "dev-user"


@router.post("/chat/stream", response_model=chat_response.ChatResponse)
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
