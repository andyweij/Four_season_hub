from typing import Protocol

from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


class ModelCatalogRepository(Protocol):
    async def get_by_name  (
        self,
        model_name: str,
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
