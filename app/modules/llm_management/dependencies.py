from typing import Annotated

from fastapi import Depends, Request

from app.modules.llm_management.services.model_catalog_service import (
    ModelCatalogService,
)


def get_model_catalog_service(
    request: Request,
) -> ModelCatalogService:
    return ModelCatalogService(
        repository=request.app.state.model_catalog
    )


ModelCatalogServiceDependency = Annotated[
    ModelCatalogService,
    Depends(get_model_catalog_service),
]