from dataclasses import dataclass

from app.modules.llm_management.bootstrap import build_llm_management_services, LlmManagementServices, \
    shutdown_llm_management

from app.infrastructure.config.settings import Settings
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.database import build_mongo_client, get_mongo_database
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.chat.bootstrap import build_chat_services, ChatServices


@dataclass
class AppServices:
    llm_management: LlmManagementServices
    chat: ChatServices
    mongo_client: AsyncIOMotorClient
    http_client: httpx.AsyncClient


async def build_app_services(settings: Settings) -> AppServices:
    llm_management = await build_llm_management_services(settings)
    mongo_client = build_mongo_client(settings)
    database = get_mongo_database(mongo_client, settings)
    http_client = httpx.AsyncClient()
    inference_client = InferenceClient(http_client)

    chat = await build_chat_services(
        database=database,
        registry_service=llm_management.registry_service,
        inference_client=inference_client,
    )
    return AppServices(
        llm_management=llm_management,
        chat=chat,
        mongo_client=mongo_client,
        http_client=http_client,
    )


async def shutdown_app_services(services: AppServices) -> None:
    await shutdown_llm_management(services.llm_management)
    await services.http_client.aclose()
    services.mongo_client.close()
