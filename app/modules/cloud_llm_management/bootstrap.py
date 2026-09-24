import base64
import binascii
from pydantic import Secret, SecretStr
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .infrastructure.persistence.postgres.cloud_llm_repository import PostgresCloudLLMRepository
from .infrastructure.security.aes_gcm_credential_cipher import AesGcmCredentialCipher
from .services.cloud_llm_mgt_service import CloudLLMManagementService
from dataclasses import dataclass


@dataclass
class CloudLlmManagementServices:
    management_service: CloudLLMManagementService


def build_cloud_llm_management_service(
        session_factory: async_sessionmaker[AsyncSession],
        encryption_keys: dict[int, bytes],
        current_key_version: int,
) -> CloudLlmManagementServices:
    repository = PostgresCloudLLMRepository(
        session_factory=session_factory,
    )

    credential_cipher = AesGcmCredentialCipher(
        keys=encryption_keys,
        current_version=current_key_version,
    )

    management_service = CloudLLMManagementService(
        repository=repository,
        credential_cipher=credential_cipher,
    )

    return CloudLlmManagementServices(
        management_service=management_service,
    )


def decode_aes_256_key(
        secret: SecretStr,
) -> bytes:
    encoded_key = secret.get_secret_value()

    try:
        decoded_key = base64.b64decode(
            encoded_key,
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "Cloud LLM encryption key "
            "must be valid Base64"
        ) from exc

    if len(decoded_key) != 32:
        raise ValueError(
            "Cloud LLM encryption key "
            "must decode to exactly 32 bytes"
        )

    return decoded_key
