import logging

from fastapi import APIRouter

from app.modules.llm_management.dependencies import (
    ModelCatalogServiceDependency,
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
@router.get("/available-models")
async def get_available_models(
        service: ModelCatalogServiceDependency,
) -> AvailableModelsResponse:
    models = await service.list_models()

    response_models = [
        AvailableModelResponse(
            model_key=model.model_key,
            model_type=model.model_type,
            artifact_name=model.artifact_name,
            engine_type=model.engine_type,
            size=model.size,
            max_images=model.max_images,
            is_chat_model=model.is_chat_model,
            supports_reasoning=model.supports_reasoning,
            supports_reasoning_effort=(
                model.supports_reasoning_effort
            ),
        )
        for model in models
    ]

    return AvailableModelsResponse(
        models=response_models,
        total=len(response_models),
    )
