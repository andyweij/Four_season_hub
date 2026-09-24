from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.infrastructure.config.settings import Settings


def build_mongo_client(settings: Settings) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.mongo_url.get_secret_value())


def get_mongo_database(client: AsyncIOMotorClient, settings: Settings) -> AsyncIOMotorDatabase:
    return client[settings.mongo_db_name]