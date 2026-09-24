from typing import Annotated

from fastapi import Depends, Request

from app.infrastructure.keycloak.admin_client import (
    KeycloakAdminClient,
)


def get_keycloak_admin_client(
    request: Request,
) -> KeycloakAdminClient:
    return request.app.state.keycloak_admin_client


KeycloakAdminClientDependency = Annotated[
    KeycloakAdminClient,
    Depends(get_keycloak_admin_client),
]