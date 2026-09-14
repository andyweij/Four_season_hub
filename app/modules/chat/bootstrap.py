from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.infrastructure.config.settings import Settings
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.chat.repositories.conversation_repository import ConversationRepository
from app.modules.chat.repositories.message_repository import MessageRepository
from app.modules.chat.services.conversation_service import ConversationService
from app.modules.chat.services.chat_stream_service import ChatStreamService


@dataclass
class ChatServices:
    conversation_repository: ConversationRepository
    message_repository: MessageRepository
    conversation_service: ConversationService
    chat_stream_service: ChatStreamService


async def build_chat_services(
        settings: Settings,
        database: AsyncIOMotorDatabase,
        registry_service: ModelRegistryService,
        inference_client: InferenceClient,
) -> ChatServices:
    conversation_repository = ConversationRepository(database)
    message_repository = MessageRepository(database)

    await conversation_repository.ensure_indexes()
    await message_repository.ensure_indexes()

    conversation_service = ConversationService(
        conversation_repository=conversation_repository,
        message_repository=message_repository
    )
    chat_stream_service = ChatStreamService(
        registry_service=registry_service,
        conversation_service=conversation_service,
        inference_client=inference_client,
    )

    return ChatServices(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        conversation_service=conversation_service,
        chat_stream_service=chat_stream_service,
    )
