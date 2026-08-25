from typing import Protocol

from app.modules.llm_management.domain.model_instance import ComponentType, ModelRuntimeStatus
from app.modules.llm_management.domain.model_instance import ModelInstance


class RuntimeInspector(Protocol):
    def inspect(
            self,
            model_status: str,
    ) -> ModelRuntimeStatus:
        ...

    def get_status(self, container_name: str) -> ModelRuntimeStatus:
        ...

    def list_hub_containers(
            self,
            component: ComponentType | None = None,
    ) -> list[ModelInstance]:
        ...
