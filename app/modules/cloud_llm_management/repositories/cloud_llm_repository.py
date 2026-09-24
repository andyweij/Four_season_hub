from typing import Protocol

from ..domain.cloud_llm import CloudLLM
from ..domain.encrypted_credential import (
    EncryptedCredential,
)


class CloudLLMRepository(Protocol):
    async def list_all(self) -> list[CloudLLM]:
        ...

    async def get_by_id(
        self,
        connection_id: str,
    ) -> CloudLLM | None:
        ...

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