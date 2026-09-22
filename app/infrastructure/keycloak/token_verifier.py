import asyncio
from typing import Any

import httpx
import jwt

from app.security.models import CurrentUser
import logging

logger = logging.getLogger("app.security")


class InvalidAccessTokenError(Exception):
    pass


class KeycloakTokenVerifier:
    def __init__(
            self,
            http_client: httpx.AsyncClient,
            jwks_url: str,
            issuer: str,
            audience: str,
    ) -> None:
        self._http_client = http_client
        self._jwks_url = jwks_url
        self._issuer = issuer
        self._audience = audience

        self._keys: dict[str, Any] = {}
        self._refresh_lock = asyncio.Lock()

    async def verify(self, token: str) -> CurrentUser:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            algorithm = header.get("alg")

            if not kid:
                raise InvalidAccessTokenError(
                    "Token does not contain kid"
                )

            if algorithm != "RS256":
                raise InvalidAccessTokenError(
                    "Unsupported signing algorithm"
                )

            public_key = await self._get_public_key(kid)

            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": ["sub", "exp", "iat"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

            return self._to_current_user(claims)

        except InvalidAccessTokenError:
            raise
        except jwt.ExpiredSignatureError as exc:
            raise InvalidAccessTokenError(
                "Access token has expired"
            ) from exc
        except jwt.InvalidAudienceError as exc:
            unverified_claims = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )

            logger.warning(
                "JWT audience mismatch expected=%r actual=%r azp=%r",
                self._audience,
                unverified_claims.get("aud"),
                unverified_claims.get("azp"),
            )

            raise InvalidAccessTokenError(
                "Invalid token audience"
            ) from exc

    async def _get_public_key(self, kid: str) -> Any:
        existing_key = self._keys.get(kid)
        if existing_key is not None:
            return existing_key

        async with self._refresh_lock:
            # 其他 request 可能已經完成更新
            existing_key = self._keys.get(kid)
            if existing_key is not None:
                return existing_key

            await self._refresh_jwks()

            public_key = self._keys.get(kid)
            if public_key is None:
                raise InvalidAccessTokenError(
                    "Unknown token signing key"
                )

            return public_key

    async def _refresh_jwks(self) -> None:
        response = await self._http_client.get(
            self._jwks_url,
            timeout=10.0,
        )
        response.raise_for_status()

        jwks = response.json()
        refreshed_keys: dict[str, Any] = {}

        for key_data in jwks.get("keys", []):
            kid = key_data.get("kid")
            key_use = key_data.get("use")
            algorithm = key_data.get("alg")

            if not kid:
                continue

            # 只載入 JWT 簽章驗證用的 RS256 Key
            if key_use != "sig":
                continue

            if algorithm != "RS256":
                continue

            refreshed_keys[kid] = jwt.PyJWK.from_dict(
                key_data,
                algorithm="RS256",
            ).key

        self._keys = refreshed_keys

    def _to_current_user(
            self,
            claims: dict[str, Any],
    ) -> CurrentUser:
        roles: set[str] = set()

        realm_access = claims.get("realm_access", {})
        roles.update(realm_access.get("roles", []))

        resource_access = claims.get("resource_access", {})
        api_access = resource_access.get(self._audience, {})
        roles.update(api_access.get("roles", []))

        return CurrentUser(
            subject=claims["sub"],
            username=claims.get("preferred_username"),
            email=claims.get("email"),
            roles=roles,
            claims=claims,
        )
