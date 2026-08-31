from typing import Protocol

from app.modules.llm_management.domain.models import ModelCatalogEntry
from app.modules.llm_management.domain.model_instance import ModelInstance


class ModelLauncher(Protocol):
    async def launch(
            self,
            catalog: ModelCatalogEntry,
            effective_config: dict,
            port: int,
    ) -> ModelInstance:
        ...