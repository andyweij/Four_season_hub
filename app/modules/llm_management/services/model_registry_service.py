from app.modules.llm_management.domain.artifact import ArtifactStatus
from app.modules.llm_management.domain.managed_model import ManagedModel
from app.modules.llm_management.repositories.model_catalog import ModelCatalogRepository
from app.modules.llm_management.runtimes.base import RuntimeInspector
from app.modules.llm_management.services.model_artifact_service import ModelArtifactService


class ModelRegistryService:
    def __init__(
            self,
            model_catalog: ModelCatalogRepository,
            artifact_service: ModelArtifactService,
            runtime_inspector: RuntimeInspector,
            endpoint_host: str,
    ):
        self._model_catalog = model_catalog
        self._artifact_service = artifact_service
        self._runtime_inspector = runtime_inspector
        self._endpoint_host = endpoint_host
        self._registry: dict[str, ManagedModel] = {}

    async def build_registry(self) -> dict[str, ManagedModel]:
        catalog_entries = await self._model_catalog.list_all()
        artifact_results = await self._artifact_service.check_all()
        instances = await self._runtime_inspector.list_hub_containers()

        artifact_by_key = {r.model_key: r for r in artifact_results}
        instance_by_name = {i.name: i for i in instances}

        self._registry = {
            entry.model_key: ManagedModel(
                catalog=entry,
                download_status=artifact_by_key[entry.model_key].status
                if entry.model_key in artifact_by_key else ArtifactStatus.MISSING,
                instance=instance_by_name.get(entry.model_key),
                endpoint_host=self._endpoint_host,
            )
            for entry in catalog_entries
        }
        return self._registry

    async def refresh_instance(self, container_name: str) -> None:
        """Docker event 觸發時呼叫，只更新單一 model 的 runtime 狀態。"""
        model = self._registry.get(container_name)
        if model is None:
            return
        model.instance = await self._runtime_inspector.get_instance(container_name)

    def get(self, model_key: str) -> ManagedModel | None:
        return self._registry.get(model_key)

    def get_all(self) -> dict[str, ManagedModel]:
        return self._registry
