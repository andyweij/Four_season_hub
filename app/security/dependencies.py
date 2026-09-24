from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.infrastructure.keycloak.token_verifier import (
    InvalidAccessTokenError,
    KeycloakTokenVerifier,
)
from app.security.models import CurrentUser
import logging

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_verifier(
        request: Request,
) -> KeycloakTokenVerifier:
    return request.app.state.token_verifier


async def get_current_user(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(bearer_scheme),
        ],
        verifier: Annotated[
            KeycloakTokenVerifier,
            Depends(get_token_verifier),
        ],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await verifier.verify(credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUserDependency = Annotated[
    CurrentUser,
    Depends(get_current_user),
]


def require_roles(
        *required_roles: str,
) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    async def dependency(
            current_user: CurrentUserDependency,
    ) -> CurrentUser:
        missing_roles = (
                set(required_roles) - current_user.roles
        )
        if missing_roles:
            logger.warning("User %s is missing roles: %s", current_user.subject, missing_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return dependency
