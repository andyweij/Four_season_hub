from app.modules.llm_management.domain.artifact import ArtifactStatus
from app.modules.llm_management.domain.managed_model import ManagedModel
from app.modules.llm_management.repositories.model_catalog import ModelCatalogRepository
from app.modules.llm_management.runtimes.base import RuntimeInspector
from app.modules.llm_management.services.model_artifact_service import ModelArtifactService
from app.modules.llm_management.services.model_health_watcher import ModelHealthWatcher
from app.modules.llm_management.domain.enums import ModelRuntimeStatus
from dataclasses import dataclass
from typing import Any
import logging

logger = logging.getLogger("app")


@dataclass
class ReadyModel:
    model: ManagedModel
    endpoint: str  # 注意：這裡是 str，不是 str | None——型別本身就保證了「一定有值」


class ModelRegistryService:
    def __init__(
            self,
            model_catalog: ModelCatalogRepository,
            artifact_service: ModelArtifactService,
            runtime_inspector: RuntimeInspector,
            endpoint_host: str,
            container_prefix: str,
            llm_engine_type: str,
            health_watcher: ModelHealthWatcher,
    ):
        self._model_catalog = model_catalog
        self._artifact_service = artifact_service
        self._runtime_inspector = runtime_inspector
        self._endpoint_host = endpoint_host
        self._container_prefix = container_prefix
        self._llm_engine_type = llm_engine_type
        self._health_watcher = health_watcher
        self._registry: dict[str, ManagedModel] = {}

    async def build_registry(self) -> dict[str, ManagedModel]:
        catalog_entries = await self._model_catalog.list_all()
        artifact_results = await self._artifact_service.check_all()
        instances = await self._runtime_inspector.list_running_instances()

        artifact_by_key = {r.model_name: r for r in artifact_results}
        instance_by_name = {i.name: i for i in instances}

        self._registry = {
            entry.model_name: ManagedModel(
                catalog=entry,
                context_len=self._extract_config_from_catalog(entry.launch_config.args),
                download_status=artifact_by_key[entry.model_name].status
                if entry.model_name in artifact_by_key else ArtifactStatus.MISSING,
                instance=instance_by_name.get(
                    self._container_prefix + "_" + entry.model_name if self._container_prefix else entry.model_name),
                endpoint_host=self._endpoint_host,
                effective_launch_config=entry.launch_config.model_copy(deep=True),  # Deep Copy，深層複製
            )
            for entry in catalog_entries
        }
        for model in self._registry.values():
            if model.instance is not None and model.instance.status == ModelRuntimeStatus.STARTING:
                self._health_watcher.watch(
                    model.catalog.model_name,
                    model.instance.public_port,
                    self.update_instance_status
                )

        return self._registry

    async def refresh_instance(self, container_name: str) -> None:
        """Docker event 觸發時呼叫，只更新單一 model 的 runtime 狀態。"""
        prefix = self._container_prefix + "_"
        model_name = container_name.removeprefix(prefix) if container_name.startswith(prefix) else container_name
        model = self._registry.get(model_name)
        if model is None:
            return
        model.instance = await self._runtime_inspector.get_instance(container_name)

    def get(self, model_name: str) -> ManagedModel | None:
        return self._registry.get(model_name)

    def get_all(self) -> dict[str, ManagedModel]:
        return self._registry

    def update_instance_status(self, model_name: str, status: ModelRuntimeStatus) -> None:
        model = self._registry.get(model_name)
        if model is not None and model.instance is not None:
            model.instance.status = status

    def get_ready_chat_model(self, model_name: str) -> ReadyModel | None:
        model = self._registry.get(model_name)
        if model is None or model.instance is None:
            return None
        endpoint = model.endpoint
        if endpoint is None:
            return None
        if not model.catalog.is_chat_model:
            return None
        if model.instance.status != ModelRuntimeStatus.READY:
            return None
        return ReadyModel(model=model, endpoint=endpoint)

    def get_all_running_instances(self) -> list[str]:
        """
        取得所有正在運行的模型名稱列表，僅包含狀態為 READY 的模型。
        """
        running_models = []
        for model in self._registry.values():
            if model.instance is not None and model.instance.status == ModelRuntimeStatus.READY:
                running_models.append(model.catalog.model_name)
        return running_models

    def _extract_config_from_catalog(self, catalog_args: dict[str, Any]) -> int:
        key = "max-model-len" if self._llm_engine_type == "vllm" else "ctx-size"
        return catalog_args.get(key, -1)