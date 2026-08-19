from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.infrastructure.config.settings import CacheBackend, get_settings
from app.modules.llm_management.factories import (
    build_model_catalog,
    build_runtime_cache,
    build_runtime_inspector,
    build_artifact_inspector,
)
from app.modules.llm_management.services.model_artifact_service import (
    ModelArtifactService,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    redis_client = None

    if settings.cache_backend == CacheBackend.REDIS:
        redis_client = Redis.from_url(
            settings.redis_url.get_secret_value(),
            decode_responses=True,
        )

    app.state.settings = settings

    app.state.model_catalog = build_model_catalog(
        settings
    )

    app.state.runtime_cache = build_runtime_cache(
        settings,
        redis_client=redis_client,
    )

    app.state.runtime_inspector = build_runtime_inspector(
        settings
    )

    artifact_inspector = build_artifact_inspector(
        settings
    )

    artifact_service = ModelArtifactService(
        model_catalog=app.state.model_catalog,
        artifact_inspector=artifact_inspector,
    )

    artifact_results = []

    if settings.model_artifact_check_on_startup:
        artifact_results = await artifact_service.check_all()

    app.state.model_artifacts = {
        result.model_key: result
        for result in artifact_results
    }

    yield

    if redis_client is not None:
        await redis_client.aclose()
