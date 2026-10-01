import asyncio
import json
import os
import tempfile
from pathlib import Path
from collections.abc import Iterable

from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


class InMemoryModelCatalog:
    def __init__(
        self,
        entries: Iterable[ModelCatalogEntry],
        catalog_path: Path | None = None,
    ):
        self._catalog_path = catalog_path.resolve() if catalog_path else None
        self._lock = asyncio.Lock()
        self._entries = {
            entry.model_name: entry
            for entry in entries
        }

    async def get_by_name(
        self,
        model_name: str,
    ) -> ModelCatalogEntry | None:
        return self._entries.get(model_name)

    async def list_all(
        self,
    ) -> list[ModelCatalogEntry]:
        return list(self._entries.values())

    async def remove(self, model_name: str) -> bool:
        """Remove registration only; preserve artifact files and other JSON entries."""
        async with self._lock:
            if model_name not in self._entries:
                return False
            if self._catalog_path:
                await asyncio.to_thread(self._remove_from_file, model_name)
            del self._entries[model_name]
            return True

    def _remove_from_file(self, model_name):
        path = self._catalog_path
        before = path.read_bytes()
        data = json.loads(before.decode("utf-8-sig"))
        data.pop(model_name, None)
        fd, temporary = tempfile.mkstemp(prefix=".catalog-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            if path.read_bytes() != before:
                raise ValueError("Catalog changed during deletion; retry after refreshing.")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
