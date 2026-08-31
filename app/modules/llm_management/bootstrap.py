import asyncio
from dataclasses import dataclass

import docker

from app.infrastructure.config.settings import Settings
from app.modules.llm_management.domain.enums import ComponentType
from app.modules.llm_management.factories import (
    build_artifact_inspector,
    build_docker_client,
    build_docker_launcher,
    build_model_catalog,
    build_runtime_inspector,
)
from app.modules.llm_management.repositories.model_catalog import ModelCatalogRepository
from app.modules.llm_management.runtimes.event_watcher import DockerEventWatcher
from app.modules.llm_management.services.model_activation_service import ModelActivationService
from app.modules.llm_management.services.model_artifact_service import ModelArtifactService
from app.modules.llm_management.services.model_health_watcher import ModelHealthWatcher
from app.modules.llm_management.services.model_registry_service import ModelRegistryService

@dataclass
class LlmManagementServices:
    model_catalog: ModelCatalogRepository
    registry_service: ModelRegistryService
    activation_service: ModelActivationService
    event_watcher: DockerEventWatcher | None
    docker_client: docker.DockerClient | None



async def build_llm_management_services(settings: Settings) -> LlmManagementServices:
    model_catalog = build_model_catalog(settings)
    artifact_inspector = build_artifact_inspector(settings)

    docker_client = build_docker_client(settings)
    runtime_inspector = build_runtime_inspector(settings, docker_client)
    model_launcher = build_docker_launcher(settings, docker_client)

    artifact_service = ModelArtifactService(
        model_catalog=model_catalog,
        artifact_inspector=artifact_inspector,
        model_instances=await runtime_inspector.list_running_instances(ComponentType.MODEL),
    )

    health_watcher = ModelHealthWatcher(
        endpoint_host=settings.model_endpoint_host,
        health_check_interval_seconds=settings.model_health_check_interval_seconds,
        startup_timeout_seconds=settings.model_startup_timeout_seconds,
    )

    registry_service = ModelRegistryService(
        model_catalog=model_catalog,
        artifact_service=artifact_service,
        runtime_inspector=runtime_inspector,
        endpoint_host=settings.model_endpoint_host,
        health_watcher=health_watcher,
    )
    await registry_service.build_registry()

    activation_service = ModelActivationService(
        launcher=model_launcher,
        registry_service=registry_service,
        health_watcher=health_watcher,
        endpoint_host=settings.model_endpoint_host,
        runtime_inspector=runtime_inspector,
    )

    event_watcher = None
    if docker_client is not None:
        event_watcher = DockerEventWatcher(docker_client, on_event=registry_service.refresh_instance)
        event_watcher.start(loop=asyncio.get_running_loop())

    return LlmManagementServices(
        model_catalog=model_catalog,
        docker_client=docker_client,
        registry_service=registry_service,
        activation_service=activation_service,
        event_watcher=event_watcher,
    )


async def shutdown_llm_management(services: LlmManagementServices) -> None:
    if services.event_watcher is not None:
        services.event_watcher.stop()
    if services.docker_client is not None:
        services.docker_client.close()