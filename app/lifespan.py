from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.bootstrap import build_app_services, shutdown_app_services
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings

    services = await build_app_services(settings)
    app.state.model_catalog = services.llm_management.model_catalog
    app.state.docker_client = services.llm_management.docker_client
    app.state.model_registry_service = services.llm_management.registry_service
    app.state.model_activation_service = services.llm_management.activation_service
    app.state.event_watcher = services.llm_management.event_watcher

    logger.info(
        "Model registry initialized with %d models",
        len(services.llm_management.registry_service.get_all()),
    )

    yield

    await shutdown_app_services(services)