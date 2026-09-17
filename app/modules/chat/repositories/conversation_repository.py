from datetime import datetime, UTC

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.modules.chat.domain.conversation import Conversation
from app.modules.chat.exceptions import ConversationAccessDeniedError
import logging

logger = logging.getLogger("app")


class ConversationRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self._collection = database["conversations"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("user_id", 1), ("updated_at", -1)])

    async def create(self, user_id: str, model: str, title: str) -> Conversation:
        now = datetime.now(UTC)
        doc = {
            "user_id": user_id,
            "title": title,
            "model": model,
            "message_seq": 0,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_domain(doc)

    async def get_owned(self, conversation_id: str, user_id: str) -> Conversation | None:
        doc = await self._collection.find_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        )
        return self._to_domain(doc) if doc else None

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[Conversation]:
        cursor = self._collection.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
        return [self._to_domain(doc) async for doc in cursor]

    async def allocate_sequence(self, conversation_id: str, user_id: str) -> int:
        doc = await self._collection.find_one_and_update(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {"$inc": {"message_seq": 1}, "$set": {"updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise ConversationAccessDeniedError(conversation_id)
        return doc["message_seq"]

    @staticmethod
    def _to_domain(doc: dict) -> Conversation:
        return Conversation(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            title=doc.get("title"),
            model=doc["model"],
            message_seq=doc["message_seq"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
