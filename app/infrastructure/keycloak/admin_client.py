import asyncio
import time
from typing import Any

import httpx


class KeycloakAdminClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret

        self._access_token: str | None = None
        self._expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def create_user(
        self,
        *,
        username: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        password: str | None = None,
        temporary_password: bool = True,
    ) -> str:
        payload: dict[str, Any] = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": False,
        }

        if password is not None:
            payload["credentials"] = [
                {
                    "type": "password",
                    "value": password,
                    "temporary": temporary_password,
                }
            ]

        response = await self._request(
            "POST",
            f"/admin/realms/{self._realm}/users",
            json=payload,
        )

        location = response.headers.get("Location")
        if not location:
            raise RuntimeError(
                "Keycloak did not return created user location"
            )

        return location.rstrip("/").split("/")[-1]

    async def get_user(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        response = await self._request(
            "GET",
            f"/admin/realms/{self._realm}/users/{user_id}",
        )
        return response.json()

    async def list_users(
        self,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {"search": search} if search else None

        response = await self._request(
            "GET",
            f"/admin/realms/{self._realm}/users",
            params=params,
        )
        return response.json()

    async def update_user(
        self,
        user_id: str,
        changes: dict[str, Any],
    ) -> None:
        await self._request(
            "PUT",
            f"/admin/realms/{self._realm}/users/{user_id}",
            json=changes,
        )

    async def set_enabled(
        self,
        user_id: str,
        enabled: bool,
    ) -> None:
        await self.update_user(
            user_id,
            {"enabled": enabled},
        )

    async def reset_password(
        self,
        user_id: str,
        password: str,
        temporary: bool = True,
    ) -> None:
        await self._request(
            "PUT",
            (
                f"/admin/realms/{self._realm}"
                f"/users/{user_id}/reset-password"
            ),
            json={
                "type": "password",
                "value": password,
                "temporary": temporary,
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        access_token = await self._get_access_token()

        response = await self._http_client.request(
            method,
            f"{self._base_url}{path}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=15.0,
            **kwargs,
        )

        response.raise_for_status()
        return response

    async def _get_access_token(self) -> str:
        now = time.monotonic()

        if (
            self._access_token is not None
            and now < self._expires_at
        ):
            return self._access_token

        async with self._token_lock:
            now = time.monotonic()

            if (
                self._access_token is not None
                and now < self._expires_at
            ):
                return self._access_token

            token_url = (
                f"{self._base_url}/realms/{self._realm}"
                "/protocol/openid-connect/token"
            )

            response = await self._http_client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=10.0,
            )
            response.raise_for_status()

            token_data = response.json()
            expires_in = int(token_data["expires_in"])

            self._access_token = token_data["access_token"]
            self._expires_at = (
                time.monotonic() + max(expires_in - 30, 1)
            )

            return self._access_token

    async def get_user_realm_roles(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """
        取得使用者擁有的所有有效 Realm Roles（包含直接指派與透過群組/複合角色繼承）。
        """
        response = await self._request(
            "GET",
            f"/admin/realms/{self._realm}/users/{user_id}/role-mappings/realm/composite",
        )
        return response.json()