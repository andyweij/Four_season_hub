import asyncio
import docker

from app.modules.llm_management.domain.models import ModelCatalogEntry

from app.modules.llm_management.domain.model_instance import ModelInstance


class DockerModelLauncher:
    def __init__(self, client: docker.DockerClient):
        self.client = client

    async def launch(self, catalog, effective_config, port) -> ModelInstance:
        return await asyncio.to_thread(self._launch_sync, catalog, effective_config, port)

    def _launch_sync(self, catalog: ModelCatalogEntry, effective_config, port) -> ModelInstance:
        # 之後接：組 docker run 參數（image / volumes / labels / env / device_requests）
        engine_image_name = catalog.engine_image_name

        # self.client.containers.run(volumes=)
