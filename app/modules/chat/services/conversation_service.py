from app.modules.chat.repositories.message_repository import MessageRepository
from app.modules.chat.repositories.conversation_repository import ConversationRepository
from datetime import datetime, UTC
from app.modules.chat.domain.conversation import Conversation
from bson import ObjectId
from app.modules.chat.domain.message import ContentPart, Message
from app.modules.chat.domain.enums import MessageStatus, MessageRole, ChatContentType
from app.modules.chat.schemas.chat_request import ChatMessage


class ConversationService:
    def __init__(self, conversation_repository: ConversationRepository,
                 message_repository: MessageRepository
                 ):
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository

    async def create_conversation(self, user_id: str, model_name: str, inference_message: ChatMessage,
                                  title: str = "") -> tuple[Conversation, Message] | None:
        conversation = await self.conversation_repository.create(user_id, model_name, title)

        if conversation.id != "":
            message = await self.add_user_message(conversation.id, user_id, self._extract_content(inference_message))
            return conversation, message
        return None

    async def get_conversation_list(self, user_id: str) -> list[Conversation]:
        return await self.conversation_repository.list_for_user(user_id)

    async def get_conversation_by_id(self, conversation_id: str) -> Conversation:
        ...

    async def _record_message(
            self,
            conversation_id: str,
            user_id: str,
            role: MessageRole,
            content: list[ContentPart],
            model: str | None = None,
            finish_reason: str | None = None,
            usage: dict | None = None,
    ) -> Message:
        sequence = await self.conversation_repository.allocate_sequence(conversation_id, user_id)
        message = Message(
            id=str(ObjectId()),
            conversation_id=conversation_id,
            user_id=user_id,
            sequence=sequence,
            role=role,
            content=content,
            model=model,
            finish_reason=finish_reason,
            usage=usage,
            status=MessageStatus.COMPLETE,
            created_at=datetime.now(UTC),
        )
        await self.message_repository.insert(conversation_id, user_id, message)
        return message

    async def add_user_message(self, conversation_id: str, user_id: str, content: list[ContentPart]) -> Message:
        return await self._record_message(conversation_id, user_id, MessageRole.USER,
                                          content=content)

    async def add_assistant_message(
            self,
            conversation_id: str,
            user_id: str,
            content: list[ContentPart],
            model: str,
            finish_reason: str | None,
            usage: dict | None,
    ) -> Message:
        return await self._record_message(
            conversation_id, user_id, MessageRole.ASSISTANT, content,
            model=model, finish_reason=finish_reason, usage=usage,
        )

    @staticmethod
    def _extract_content(message: ChatMessage) -> list[ContentPart]:
        return [ContentPart(type=part.type, text=part.text) for part in message.content]
