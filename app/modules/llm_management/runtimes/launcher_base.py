from typing import Protocol

from app.modules.llm_management.domain.models import ModelCatalogEntry
from app.modules.llm_management.domain.model_instance import ModelInstance
from app.modules.llm_management.domain.launch_config import LaunchConfig

class ModelLauncher(Protocol):
    async def launch(
            self,
            catalog: ModelCatalogEntry,
            effective_config: LaunchConfig,
            port: int,
    ) -> ModelInstance:
        ...