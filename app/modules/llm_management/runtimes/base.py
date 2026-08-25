from typing import Protocol

from app.modules.llm_management.domain.model_instance import ComponentType, ModelRuntimeStatus
from app.modules.llm_management.domain.model_instance import ModelInstance


class RuntimeInspector(Protocol):
    async def get_status(self, container_name: str) -> ModelRuntimeStatus: ...

    async def list_hub_containers(self, component: ComponentType | None = None) -> list[ModelInstance]: ...

    async def get_instance(self, container_name: str) -> ModelInstance | None: ...

    async def inspect(
            self,
            model_status: str,
    ) -> ModelRuntimeStatus:
        ...
