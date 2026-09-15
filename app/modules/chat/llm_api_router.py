import uuid

from app.modules.chat.schemas.chat_request import ChatRequest
from app.modules.chat.schemas import chat_response
from fastapi import APIRouter
from app.modules.chat.services.chat_stream_service import ChatStreamService
import logging

logger = logging.getLogger("app")
router = APIRouter(
    tags=["Chat"],
)


@router.post("/stream/chat", response_model=chat_response.ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the model.

    - **model**: The model to use for the chat.
    - **message**: The message to send to the model.
    - **stream**: Whether to stream the response or not.
    - **parameters**: The generation parameters to use for the chat.
    """

    contents = list(map(lambda msg: msg.content, request.message))
    logger.info("Received message: %s", contents)
    await ChatStreamService.chat_stream(request)
    user_question = request.message[-1].content if request.message else ""
    
    return chat_response.ChatResponse(
        request_id=str(uuid.uuid4()),
        conversation_id=str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
        model=request.model,
        message=chat_response.ChatMessageResponse(
            role="assistant",
            content=f"Echo: {user_question}",  # 將取出的內容放進回傳結果
        ),
        finish_reason="stop",
    )
