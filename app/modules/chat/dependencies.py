from typing import Annotated
from fastapi import Depends, Request
from app.modules.chat.services.chat_stream_service import ChatStreamService
from app.modules.chat.services.chat_model_service import ChatModelService


def get_chat_stream_service(request: Request) -> ChatStreamService:
    return request.app.state.chat_stream_service


def get_chat_model_service(request: Request) -> ChatModelService:
    return request.app.state.chat_model_service


ChatStreamServiceDependency = Annotated[
    ChatStreamService,
    Depends(get_chat_stream_service),
]

ChatModelServiceDependency = Annotated[
    ChatModelService,
    Depends(get_chat_model_service)
]
