# domain/managed_model.py
from datetime import datetime

from pydantic import BaseModel

from app.modules.llm_management.domain.artifact import ArtifactStatus
from app.modules.llm_management.domain.models import ModelCatalogEntry
from app.modules.llm_management.domain.model_instance import ModelInstance
from typing import Any


class ManagedModel(BaseModel):
    catalog: ModelCatalogEntry

    download_status: ArtifactStatus
    downloaded_at: datetime | None = None

    instance: ModelInstance | None = None  # 容器還沒建立/還沒啟動時就是 None
    endpoint_host: str
    effective_launch_config: dict[str, Any]  # 新增：目前生效中的啟動設定

    @property
    def endpoint(self) -> str | None:
        if self.instance is None or self.instance.public_port == 0:
            return None
        return f"http://{self.endpoint_host}:{self.instance.public_port}"
