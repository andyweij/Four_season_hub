from sqlalchemy import select
from app.modules.cloud_llm_management.domain.encrypted_credential import EncryptedCredential
from .mappers import to_domain, to_record
from .models.cloud_llm_record import CloudLLMRecord


class PostgresCloudLLMRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def list_all(self):
        async with self._session_factory() as session:
            result = await session.execute(select(CloudLLMRecord).order_by(CloudLLMRecord.created_at.desc()))
            return [to_domain(record) for record in result.scalars().all()]

    async def get_by_id(self, connection_id):
        async with self._session_factory() as session:
            record = await session.get(CloudLLMRecord, connection_id)
            return to_domain(record) if record else None

    async def get_credential(self, connection_id):
        async with self._session_factory() as session:
            record = await session.get(CloudLLMRecord, connection_id)
            if record is None:
                return None
            return EncryptedCredential(
                ciphertext=record.encrypted_api_key, nonce=record.encryption_nonce,
                key_version=record.encryption_key_version, api_key_hint=record.api_key_hint,
            )

    async def add(self, connection, credential):
        async with self._session_factory.begin() as session:
            record = to_record(connection, credential)
            session.add(record)
            await session.flush()
            return to_domain(record)

    async def update(self, connection, credential=None):
        async with self._session_factory.begin() as session:
            record = await session.get(CloudLLMRecord, connection.id)
            if record is None:
                raise ValueError("Cloud connection was not found.")
            if credential is None:
                credential = EncryptedCredential(
                    record.encrypted_api_key, record.encryption_nonce,
                    record.encryption_key_version, record.api_key_hint,
                )
            replacement = to_record(connection, credential)
            for column in CloudLLMRecord.__table__.columns:
                if column.name != "id":
                    setattr(record, column.name, getattr(replacement, column.name))
            await session.flush()
            return to_domain(record)

    async def delete(self, connection_id):
        async with self._session_factory.begin() as session:
            record = await session.get(CloudLLMRecord, connection_id)
            if record is None:
                return False
            await session.delete(record)
            return True
