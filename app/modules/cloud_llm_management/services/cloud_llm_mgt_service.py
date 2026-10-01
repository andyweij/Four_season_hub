import logging

from app.modules.cloud_llm_management.ports.credential_cipher import CredentialCipher
from app.modules.cloud_llm_management.repositories.cloud_llm_repository import CloudLLMRepository
from app.modules.cloud_llm_management.schemas import CloudLLMList, AddLLM
from ..domain.cloud_llm import CloudLLM, Capabilities
from datetime import UTC, datetime
from uuid import uuid4

from ..domain.enums import CloudLLMStatus

logger = logging.getLogger(__name__)


class CloudLLMManagementService:
    def __init__(
            self,
            repository: CloudLLMRepository,
            credential_cipher: CredentialCipher,
    ):
        self._repository = repository
        self._credential_cipher = credential_cipher

    async def create(
            self,
            request: AddLLM,
            user_id: str,
    ) -> CloudLLM:
        plain_api_key = (
            request.api_key.get_secret_value()
        )

        credential = self._credential_cipher.encrypt(
            plain_api_key,
        )

        now = datetime.now(UTC)

        connection = CloudLLM(
            id=f"conn_{uuid4().hex}",
            name=request.name,
            provider=request.provider,
            model_name=request.model_name,
            base_url=request.base_url,
            enabled=False,
            status=CloudLLMStatus.UNTESTED,
            max_images=request.max_images,
            max_model_len=request.max_model_len,
            is_chat_model=request.is_chat_model,
            capabilities=Capabilities(
                vision=request.max_images > 0, streaming=request.is_chat_model,
                reasoning=request.supports_reasoning,
                reasoning_effort=request.supports_reasoning_effort,
                tool_calling=request.supports_tool_calling,
            ),
            api_key_hint=credential.api_key_hint,
            credential_configured=True,
            last_tested_at=None,
            last_latency_ms=None,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )

        return await self._repository.add(
            connection,
            credential,
        )

    async def get_cloud_llm_list(self) -> list[CloudLLM]:
        return await self._repository.list_all()

    async def update(self, connection_id, request):
        connection = await self._repository.get_by_id(connection_id)
        if connection is None:
            raise ValueError("Cloud connection was not found.")
        data = request.model_dump(exclude_unset=True)
        changed = any(key in data and data[key] != getattr(connection, key)
                      for key in ("model_name", "base_url")) or request.api_key is not None
        credential = None
        if "api_key" in data and request.api_key is not None:
            credential = self._credential_cipher.encrypt(request.api_key.get_secret_value())
        for key in ("name", "model_name", "base_url", "enabled"):
            if key in data:
                if data[key] is None and key != "base_url":
                    raise ValueError(f"{key} cannot be null")
                setattr(connection, key, data[key])
        if changed:
            connection.status = CloudLLMStatus.UNTESTED
            connection.last_tested_at = None
            connection.last_latency_ms = None
        if connection.enabled and connection.status == CloudLLMStatus.DISABLED:
            connection.status = CloudLLMStatus.UNTESTED
        elif not connection.enabled:
            connection.status = CloudLLMStatus.DISABLED
        connection.updated_at = datetime.now(UTC)
        return await self._repository.update(connection, credential)


    async def get(self, connection_id):
        connection = await self._repository.get_by_id(connection_id)
        if connection is None:
            raise LookupError("Cloud connection was not found.")
        return connection

    async def test(self, connection_id, http_client):
        from .connection_probe import probe_connection
        connection = await self.get(connection_id)
        credential = await self._repository.get_credential(connection_id)
        if credential is None:
            raise ValueError("Model credential is unavailable.")
        key = self._credential_cipher.decrypt(credential)
        status, latency, message = await probe_connection(http_client, connection, key)
        connection.status = status
        connection.last_tested_at = datetime.now(UTC)
        connection.last_latency_ms = latency
        connection.updated_at = datetime.now(UTC)
        await self._repository.update(connection)
        return {"status": status, "latencyMs": latency, "message": message,
                "enabled": connection.enabled, "testKind": "model_metadata"}

    async def delete(self, connection_id):
        if not await self._repository.delete(connection_id):
            raise LookupError("Cloud connection was not found.")
