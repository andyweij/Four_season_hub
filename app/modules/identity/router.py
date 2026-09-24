import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.modules.identity.dependencies import (
    KeycloakAdminClientDependency,
)
from app.modules.identity.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
)
from app.security.dependencies import (
    CurrentUserDependency,
    require_roles,
)
from app.security.models import CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users")

UserAdminDependency = Annotated[
    CurrentUser,
    Depends(require_roles("user-admin")),
]


@router.get("/me")
async def get_my_profile(
        current_user: CurrentUserDependency,
        admin_client: KeycloakAdminClientDependency,
) -> dict[str, Any]:
    user_data = await admin_client.get_user(
        current_user.subject
    )
    roles = await admin_client.get_user_realm_roles(current_user.subject)
    user_data["roles"] = [r["name"] for r in roles]
    return user_data


@router.patch("/me", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_profile(
        body: UpdateUserRequest,
        current_user: CurrentUserDependency,
        admin_client: KeycloakAdminClientDependency,
) -> Response:
    changes = body.model_dump(
        exclude_none=True,
    )

    # 一般使用者不能自行停用或啟用帳號
    changes.pop("enabled", None)

    keycloak_changes = {
        "email": changes.get("email"),
        "firstName": changes.get("first_name"),
        "lastName": changes.get("last_name"),
    }
    keycloak_changes = {
        key: value
        for key, value in keycloak_changes.items()
        if value is not None
    }

    await admin_client.update_user(
        current_user.subject,
        keycloak_changes,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
        body: CreateUserRequest,
        _: UserAdminDependency,
        admin_client: KeycloakAdminClientDependency,
) -> dict[str, str]:
    user_id = await admin_client.create_user(
        username=body.username,
        email=str(body.email),
        first_name=body.first_name,
        last_name=body.last_name,
        password=body.password,
        temporary_password=body.temporary_password,
    )

    return {"id": user_id}


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_user(
        user_id: str,
        body: UpdateUserRequest,
        _: UserAdminDependency,
        admin_client: KeycloakAdminClientDependency,
) -> Response:
    changes = body.model_dump(exclude_none=True)

    keycloak_changes = {
        "email": changes.get("email"),
        "firstName": changes.get("first_name"),
        "lastName": changes.get("last_name"),
        "enabled": changes.get("enabled"),
    }
    keycloak_changes = {
        key: value
        for key, value in keycloak_changes.items()
        if value is not None
    }

    await admin_client.update_user(
        user_id,
        keycloak_changes,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
