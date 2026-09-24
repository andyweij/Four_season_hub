from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.modules.cloud_llm_management.domain.cloud_llm import CloudLLM
from app.modules.cloud_llm_management.domain.encrypted_credential import EncryptedCredential
from app.modules.cloud_llm_management.infrastructure.persistence.postgres.mappers import to_domain
from app.modules.cloud_llm_management.infrastructure.persistence.postgres.models.cloud_llm_record import CloudLLMRecord


class PostgresCloudLLMRepository:
    def __init__(
            self,
            session_factory: async_sessionmaker[AsyncSession],
    ):
        self._session_factory = session_factory

    async def list_all(self) -> list[CloudLLM]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CloudLLMRecord)
                .order_by(
                    CloudLLMRecord.created_at.desc()
                )
            )

            return [
                to_domain(record)
                for record in result.scalars().all()
            ]

    async def get_by_id(
            self,
            connection_id: str,
    ) -> CloudLLM | None:
        pass

    async def get_credential(
            self,
            connection_id: str,
    ) -> EncryptedCredential | None:
        ...

    async def add(
            self,
            connection: CloudLLM,
            credential: EncryptedCredential,
    ) -> CloudLLM:
        ...

    async def update(
            self,
            connection: CloudLLM,
            credential: EncryptedCredential | None = None,
    ) -> CloudLLM:
        ...

    async def delete(
            self,
            connection_id: str,
    ) -> bool:
        ...
