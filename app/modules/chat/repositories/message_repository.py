from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.chat.domain.message import ContentPart, Message


class MessageRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self._collection = database["messages"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("conversation_id", 1), ("sequence", 1)], unique=True
        )

    async def insert(self, message: Message) -> None:
        doc = {
            "_id": ObjectId(message.id),
            "conversation_id": message.conversation_id,
            "user_id": message.user_id,
            "sequence": message.sequence,
            "role": message.role,
            "content": [part.model_dump() for part in message.content],
            "model": message.model,
            "finish_reason": message.finish_reason,
            "usage": message.usage,
            "status": message.status,
            "created_at": message.created_at,
        }
        await self._collection.insert_one(doc)

    async def list_for_conversation(self, conversation_id: str, user_id: str) -> list[Message]:
        cursor = self._collection.find(
            {"conversation_id": conversation_id, "user_id": user_id}
        ).sort("sequence", 1)
        return [self._to_domain(doc) async for doc in cursor]

    @staticmethod
    def _to_domain(doc: dict) -> Message:
        return Message(
            id=str(doc["_id"]),
            conversation_id=doc["conversation_id"],
            user_id=doc["user_id"],
            sequence=doc["sequence"],
            role=doc["role"],
            content=[ContentPart(**part) for part in doc["content"]],
            model=doc.get("model"),
            finish_reason=doc.get("finish_reason"),
            usage=doc.get("usage"),
            status=doc["status"],
            created_at=doc["created_at"],
        )