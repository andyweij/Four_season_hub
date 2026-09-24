from app.modules.cloud_llm_management.domain.cloud_llm import CloudLLM
from app.modules.cloud_llm_management.domain.encrypted_credential import EncryptedCredential
from app.modules.cloud_llm_management.domain.enums import CloudLLMProvider, CloudLLMStatus
from app.modules.cloud_llm_management.infrastructure.persistence.postgres.models.cloud_llm_record import CloudLLMRecord


def to_domain(
    record: CloudLLMRecord,
) -> CloudLLM:
    return CloudLLM(
        id=record.id,
        name=record.name,
        provider=CloudLLMProvider(record.provider),
        model_name=record.model_name,
        base_url=record.base_url,
        enabled=record.enabled,
        status=CloudLLMStatus(record.status),
        max_images=record.max_images,
        max_model_len=record.max_model_len,
        is_chat_model=record.is_chat_model,
        supports_reasoning=record.supports_reasoning,
        supports_reasoning_effort=(
            record.supports_reasoning_effort
        ),
        supports_tool_calling=(
            record.supports_tool_calling
        ),
        api_key_hint=record.api_key_hint,
        credential_configured=True,
        last_tested_at=record.last_tested_at,
        last_latency_ms=record.last_latency_ms,
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )

def to_record(
    connection: CloudLLM,
    credential: EncryptedCredential,
) -> CloudLLMRecord:
    return CloudLLMRecord(
        id=connection.id,
        name=connection.name,
        provider=connection.provider.value,
        model_name=connection.model_name,
        base_url=connection.base_url,
        encrypted_api_key=credential.ciphertext,
        encryption_nonce=credential.nonce,
        encryption_key_version=credential.key_version,
        api_key_hint=credential.api_key_hint,
        # ...
    )