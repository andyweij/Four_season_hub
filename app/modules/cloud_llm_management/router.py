import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status

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
    CurrentUser, Depends(require_roles("admin"))
]


@router.get("")
async def get_cloud_llm_list(cloud_llm_service: CloudLLMManagementServiceDependency, current_user: UserAdminDependency) -> list[CloudLLM]:
    logger.info("CloudLLM configured")
    return await cloud_llm_service.get_cloud_llm_list()


@router.post("",
             status_code=status.HTTP_201_CREATED,
             )
async def add_cloud_llm(add_llm: AddLLM,
                        cloud_llm_service: CloudLLMManagementServiceDependency,
                        current_user: UserAdminDependency, ) -> CloudLLM:
    logger.info(f"Adding CloudLLM: {add_llm.model_name}")
    user_name = current_user.subject
    return await cloud_llm_service.create(request=add_llm, user_id=user_name)


from app.modules.cloud_llm_management.schemas.update_cloud_llm_request import UpdateCloudLLMRequest
from fastapi import HTTPException


@router.patch("/{connection_id}")
async def update_cloud_llm(connection_id: str, body: UpdateCloudLLMRequest,
                           cloud_llm_service: CloudLLMManagementServiceDependency,
                           current_user: UserAdminDependency):
    try:
        return await cloud_llm_service.update(connection_id, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{connection_id}")
async def get_cloud_llm(connection_id: str, cloud_llm_service: CloudLLMManagementServiceDependency,
                        current_user: UserAdminDependency):
    try:
        return await cloud_llm_service.get(connection_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{connection_id}/test")
async def test_cloud_llm(connection_id: str, request: Request,
                         cloud_llm_service: CloudLLMManagementServiceDependency,
                         current_user: UserAdminDependency):
    try:
        return await cloud_llm_service.test(connection_id, request.app.state.http_client)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cloud_llm(connection_id: str, cloud_llm_service: CloudLLMManagementServiceDependency,
                           current_user: UserAdminDependency):
    try:
        await cloud_llm_service.delete(connection_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)
