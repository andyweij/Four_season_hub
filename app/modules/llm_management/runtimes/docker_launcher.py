import asyncio
import docker
from app.modules.llm_management.domain.model_instance import ModelInstance


class DockerModelLauncher:
    def __init__(self, client: docker.DockerClient):
        self.client = client

    async def launch(self, catalog, effective_config, port) -> ModelInstance:
        return await asyncio.to_thread(self._launch_sync, catalog, effective_config, port)

    def _launch_sync(self, catalog, effective_config, port) -> ModelInstance:
        # 之後接：組 docker run 參數（image / volumes / labels / env / device_requests）
        ...
