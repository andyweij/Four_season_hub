from typing import Annotated

from fastapi import Depends, Request

from app.modules.llm_management.services.model_registry_service import (
    ModelRegistryService,
)


def get_model_registry_service(request: Request) -> ModelRegistryService:
    return request.app.state.model_registry_service


ModelRegistryServiceDependency = Annotated[
    ModelRegistryService,
    Depends(get_model_registry_service),
]