from typing import Protocol

from app.modules.llm_management.domain.enums import ComponentType, ModelRuntimeStatus
from app.modules.llm_management.schemas.model_instance import ManagedInstance


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
    ) -> list[ManagedInstance]:
        ...
