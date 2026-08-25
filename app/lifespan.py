from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from redis.asyncio import Redis

from app.infrastructure.config.settings import CacheBackend, get_settings
from app.modules.llm_management.domain.enums import ComponentType
from app.modules.llm_management.factories import (
    build_model_catalog,
    build_runtime_cache,
    build_runtime_inspector,
    build_artifact_inspector,
    build_docker_client,
)
from app.modules.llm_management.services.model_artifact_service import (
    ModelArtifactService,
)
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.llm_management.runtimes.event_watcher import DockerEventWatcher
import logging

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # redis_client = None
    #
    # if settings.cache_backend == CacheBackend.REDIS:
    #     redis_client = Redis.from_url(
    #         settings.redis_url.get_secret_value(),
    #         decode_responses=True,
    #     )

    # app.state.runtime_cache = build_runtime_cache(
    #     settings,
    #     redis_client=redis_client,
    # )

    # 環境變數初始化
    app.state.settings = settings
    # 模型清單
    app.state.model_catalog = build_model_catalog(
        settings
    )
    # 檢查本地模型檔案是否完整
    artifact_inspector = build_artifact_inspector(
        settings
    )

    # runtime 初始化
    docker_client = build_docker_client(settings)
    app.state.docker_client = docker_client  # native 模式下這裡會是 None，是刻意設計

    app.state.runtime_inspector = build_runtime_inspector(settings, docker_client)

    artifact_service = ModelArtifactService(
        model_catalog=app.state.model_catalog,
        artifact_inspector=artifact_inspector,
        model_instances=app.state.runtime_inspector.list_hub_containers(ComponentType.MODEL)
    )

    registry_service = ModelRegistryService(
        model_catalog=app.state.model_catalog,
        artifact_service=artifact_service,
        runtime_inspector=app.state.runtime_inspector,
        endpoint_host=settings.model_endpoint_host,
    )
    app.state.model_registry = await registry_service.build_registry()

    app.state.event_watcher = None
    if docker_client is not None:
        watcher = DockerEventWatcher(docker_client, on_event=registry_service.refresh_instance)
        watcher.start(loop=asyncio.get_running_loop())
        app.state.event_watcher = watcher

    logger.info(
        "Model registry initialized with %d models",
        len(app.state.model_registry),
        # {k: v.model_dump() for k, v in app.state.model_registry.items()},
    )
    yield

    if app.state.event_watcher is not None:
        app.state.event_watcher.stop()

    if docker_client is not None:
        docker_client.close()

    # if redis_client is not None:
    #     await redis_client.aclose()
