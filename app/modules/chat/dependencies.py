from typing import Annotated
from fastapi import Depends, Request
from app.modules.chat.services.chat_stream_service import ChatStreamService


def get_chat_stream_service(request: Request) -> ChatStreamService:
    return request.app.state.chat_stream_service


ChatStreamServiceDependency = Annotated[
    ChatStreamService,
    Depends(get_chat_stream_service),
]