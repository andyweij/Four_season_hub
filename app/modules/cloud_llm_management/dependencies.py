from typing import Annotated

from fastapi import Depends, Request

from .services.cloud_llm_mgt_service import (
    CloudLLMManagementService,
)


def get_cloud_llm_management_service(
    request: Request,
) -> CloudLLMManagementService:
    return request.app.state.cloud_llm_management_service


CloudLLMManagementServiceDependency = Annotated[
    CloudLLMManagementService,
    Depends(get_cloud_llm_management_service),
]