import logging

from fastapi import APIRouter

from app.modules.llm_management.dependencies import (
    ModelRegistryServiceDependency,
)
from app.modules.llm_management.schemas.available_models import (
    AvailableModelsResponse,
)
from app.modules.llm_management.schemas.model_mappers import to_available_model_response

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
        to_available_model_response(model)
        for model in registry.get_all().values()
    ]

    return AvailableModelsResponse(
        models=response_models,
        total=len(response_models),
    )
