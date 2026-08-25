import logging

from fastapi import APIRouter

from app.modules.llm_management.dependencies import (
    ModelRegistryServiceDependency,
)
from app.modules.llm_management.schemas.available_models import (
    AvailableModelResponse,
    AvailableModelsResponse,
)

logger = logging.getLogger("app")
router = APIRouter()


@router.get(
    "/available-models",
    response_model=AvailableModelsResponse,
)
async def get_available_models(
        registry: ModelRegistryServiceDependency,
) -> AvailableModelsResponse:
    response_models = [
        AvailableModelResponse(
            model_key=model.catalog.model_key,
            model_type=model.catalog.model_type,
            size=model.catalog.size,
            max_images=model.catalog.max_images,
            is_chat_model=model.catalog.is_chat_model,
            supports_reasoning=model.catalog.supports_reasoning,
            supports_reasoning_effort=model.catalog.supports_reasoning_effort,
            download_status=model.download_status,
            status=model.instance.status if model.instance is not None else 'unknown',
        )
        for model in registry.get_all().values()
    ]

    return AvailableModelsResponse(
        models=response_models,
        total=len(response_models),
    )
