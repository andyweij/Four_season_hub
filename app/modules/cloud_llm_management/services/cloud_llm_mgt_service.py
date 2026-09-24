import logging

from app.modules.cloud_llm_management.ports.credential_cipher import CredentialCipher
from app.modules.cloud_llm_management.repositories.cloud_llm_repository import CloudLLMRepository
from app.modules.cloud_llm_management.schemas import CloudLLMList, AddLLM
from ..domain.cloud_llm import CloudLLM
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
            supports_reasoning=request.supports_reasoning,
            supports_reasoning_effort=(
                request.supports_reasoning_effort
            ),
            supports_tool_calling=False,
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
