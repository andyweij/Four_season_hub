from typing import Protocol

from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


class ModelCatalogRepository(Protocol):
    async def get_by_key(
        self,
        model_key: str,
    ) -> ModelCatalogEntry | None:
        ...

    async def list_all(
        self,
    ) -> list[ModelCatalogEntry]:
        ...

    async def replace_all(
        self,
        entries: list[ModelCatalogEntry],
    ) -> None:
        ...
