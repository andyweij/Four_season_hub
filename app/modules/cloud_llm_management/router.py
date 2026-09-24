import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.modules.cloud_llm_management.dependencies import CloudLLMManagementServiceDependency
from app.modules.cloud_llm_management.domain.cloud_llm import CloudLLM
from app.modules.cloud_llm_management.schemas import AddLLM
from app.security.dependencies import (
    CurrentUserDependency,
    require_roles,
)
from app.security.models import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/llm-connections",
    tags=["Cloud LLM Management"],
)

UserAdminDependency = Annotated[
    CurrentUser, Depends(require_roles("user-admin"))
]


@router.get("")
async def get_cloud_llm_list(cloud_llm_service: CloudLLMManagementServiceDependency) -> list[CloudLLM]:
    logger.info("CloudLLM configured")
    return await cloud_llm_service.get_cloud_llm_list()


@router.post("/add",
             status_code=status.HTTP_201_CREATED,
             )
async def add_cloud_llm(add_llm: AddLLM,
                        cloud_llm_service: CloudLLMManagementServiceDependency,
                        current_user: UserAdminDependency, ) -> dict:
    logger.info(f"Adding CloudLLM: {add_llm.model_name}")
    user_name = current_user.subject
    await cloud_llm_service.create(request=add_llm, user_id=user_name)
    return {"model_name": add_llm.model_name,
            "status": "added", }
