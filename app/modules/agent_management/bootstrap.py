import json
from dataclasses import dataclass
from app.modules.agent_management.repositories.json_agent_catalog import JsonAgentCatalogRepository
from app.modules.agent_management.services.agent_registry_service import AgentRegistryService
from app.modules.agent_management.services.agent_lifecycle_service import AgentLifecycleService
from app.modules.agent_execution.repositories.agent_run_repository import AgentRunRepository
from app.modules.agent_execution.services.task_policy import TaskPolicy
from app.modules.agent_execution.services.agent_run_service import AgentRunService
from app.modules.agent_execution.infrastructure.remote_agent_client import RemoteAgentExecutor
from app.modules.agent_execution.infrastructure.openai_chat_agent import OpenAIChatAgentExecutor
from app.modules.model_gateway.services.model_resolver import ModelResolver
from app.modules.model_gateway.services.model_gateway_service import ModelGatewayService
from app.modules.model_gateway.providers.openai_compatible import OpenAICompatibleProvider
from app.modules.model_gateway.providers.gemini import GeminiProvider
from app.modules.model_gateway.security.access_key_service import AccessKeyService


@dataclass
class AgentServices:
    registry: AgentRegistryService
    runs: AgentRunService
    lifecycle: AgentLifecycleService
    gateway: ModelGatewayService
    access_keys: AccessKeyService


async def build_agent_services(settings, database, http_client, llm_management, cloud):
    catalog = JsonAgentCatalogRepository(settings.agent_catalog_path)
    registry = AgentRegistryService(catalog, database)
    repository = AgentRunRepository(database)
    await repository.ensure_indexes()
    await repository.expire_stale()
    resolver = ModelResolver(llm_management.registry_service, cloud.repository)
    gemini = GeminiProvider(http_client, database)
    await gemini.ensure_indexes()
    gateway = ModelGatewayService(
        resolver, {"openai_compatible": OpenAICompatibleProvider(http_client), "gemini": gemini},
        cloud.repository, cloud.credential_cipher,
    )
    signing_key = settings.agent_signing_key.get_secret_value() if settings.agent_signing_key else None
    access = AccessKeyService(database, signing_key)
    await access.ensure_indexes()
    token = settings.agent_service_token.get_secret_value() if settings.agent_service_token else None
    credentials = json.loads(settings.agent_credentials.get_secret_value()) if settings.agent_credentials else {}
    environment = json.loads(settings.agent_runtime_environment.get_secret_value()) if settings.agent_runtime_environment else {}
    lifecycle = AgentLifecycleService(
        http_client, llm_management.docker_client, settings.container_network_name,
        repository, token, environment,
    )
    executors = {
        "hub_native": RemoteAgentExecutor(http_client, repository, access, resolver, token, credentials),
        "openai_chat": OpenAIChatAgentExecutor(http_client, credentials),
    }
    runs = AgentRunService(registry, repository, TaskPolicy(), executors,
                           resolver, lifecycle, settings.agent_gateway_profiles)
    return AgentServices(registry, runs, lifecycle, gateway, access)
