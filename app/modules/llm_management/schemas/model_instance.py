# domain/models.py 或新開一個 domain/runtime.py
from pydantic import BaseModel

from app.modules.llm_management.domain.enums import ComponentType, ModelRuntimeStatus


class ManagedInstance(BaseModel):
    id: str
    name: str
    component: ComponentType
    status: ModelRuntimeStatus
    public_port: int
    private_port: int