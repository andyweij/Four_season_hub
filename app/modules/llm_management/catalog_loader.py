import json
from pathlib import Path

from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


def load_catalog_file(
    path: Path,
) -> list[ModelCatalogEntry]:
    raw_catalog = json.loads(
        path.read_text(encoding="utf-8")
    )

    return [
        ModelCatalogEntry(
            model_key=model_key,
            **model_data,
        )
        for model_key, model_data in raw_catalog.items()
    ]