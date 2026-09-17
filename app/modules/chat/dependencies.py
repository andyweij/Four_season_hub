from typing import Annotated
from fastapi import Depends, Request
from app.modules.chat.services.chat_stream_service import ChatStreamService
from app.modules.chat.services.chat_model_service import ChatModelService
from app.modules.chat.services.conversation_service import ConversationService


def get_chat_stream_service(request: Request) -> ChatStreamService:
    return request.app.state.chat_stream_service


def get_chat_model_service(request: Request) -> ChatModelService:
    return request.app.state.chat_model_service


def get_conversation_service(request: Request) -> ConversationService:
    return request.app.state.conversation_service


ChatStreamServiceDependency = Annotated[
    ChatStreamService,
    Depends(get_chat_stream_service),
]

ChatModelServiceDependency = Annotated[
    ChatModelService,
    Depends(get_chat_model_service)
]

ConversationServiceDependency = Annotated[
    ConversationService,
    Depends(get_conversation_service)
]
