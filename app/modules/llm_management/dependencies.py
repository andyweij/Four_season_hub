from typing import Annotated

from fastapi import Depends, Request

from app.modules.llm_management.services.model_registry_service import (
    ModelRegistryService,
)
from app.modules.llm_management.services.model_activation_service import (
    ModelActivationService,
)


def get_model_registry_service(request: Request) -> ModelRegistryService:
    return request.app.state.model_registry_service


def get_model_activation_service(request: Request) -> ModelActivationService:
    return request.app.state.model_activation_service


ModelRegistryServiceDependency = Annotated[
    ModelRegistryService,
    Depends(get_model_registry_service),
]

ModelActivationServiceDependency = Annotated[
    ModelActivationService,
    Depends(get_model_activation_service),
]
