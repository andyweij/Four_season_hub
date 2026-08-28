from dataclasses import dataclass

from app.modules.llm_management.bootstrap import build_llm_management_services, LlmManagementServices

from app.infrastructure.config.settings import Settings


@dataclass
class AppServices:
    llm_management: LlmManagementServices


async def build_app_services(settings: Settings) -> AppServices:
    llm_management = await build_llm_management_services(settings)

    return AppServices(
        llm_management=llm_management,
    )