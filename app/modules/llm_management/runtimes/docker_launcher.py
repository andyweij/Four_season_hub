import asyncio
import docker
import logging
from docker.types import DeviceRequest
from app.modules.llm_management.domain.models import ModelCatalogEntry

from app.modules.llm_management.domain.model_instance import ModelInstance
from app.modules.llm_management.domain.volume_mount import VolumeMount
from app.modules.llm_management.runtimes.labels import (
    COMPONENT_LABEL, HUB_OWNER_VALUE, MANAGED_BY_LABEL,
)
from app.modules.llm_management.runtimes.launch_args import build_config_args, parse_env_list
from app.modules.llm_management.domain.enums import ComponentType, ModelRuntimeStatus

logger = logging.getLogger("app")

INTERNAL_PORT = 8000


class DockerModelLauncher:
    def __init__(self, client: docker.DockerClient, network_name: str | None = None):
        self.client = client
        self.network_name = network_name

    async def launch(self, catalog, effective_config, port) -> ModelInstance:
        return await asyncio.to_thread(self._launch_sync, catalog, effective_config, port)

    def _launch_sync(self, catalog: ModelCatalogEntry, effective_config, port) -> ModelInstance:
        # 之後接：組 docker run 參數（image / volumes / labels / env / device_requests）
        engine_image_name = catalog.engine_image_name
        model_name = catalog.model_name
        if engine_image_name is None:
            raise ValueError(f"{catalog.model_name} 沒有設定 engineImageName，無法以 docker 啟動")
        volumes = (
            effective_config.container.volumes
            if effective_config.container is not None
            else []
        )
        command = build_config_args(effective_config.args)
        command.extend(["--served-model-name", model_name])
        logger.info(
            "Launching docker model %s: image=%s command=%s",
            catalog.model_name, engine_image_name, " ".join(command),
        )
        container = self.client.containers.run(
            image=engine_image_name,
            name=catalog.model_name,
            command=command,
            environment=parse_env_list(effective_config.env),
            ports={f"{INTERNAL_PORT}/tcp": port},
            volumes=self._build_volumes(volumes),
            labels={
                MANAGED_BY_LABEL: HUB_OWNER_VALUE,
                COMPONENT_LABEL: str(ComponentType.MODEL.value),
            },
            device_requests=[DeviceRequest(count=-1, capabilities=[["gpu"]])],
            network=self.network_name,  # None 的話 docker-py 會用預設的 bridge network
            detach=True,
        )
        return ModelInstance(
            id=container.id,
            name=catalog.model_name,
            component=ComponentType.MODEL,
            status=ModelRuntimeStatus.STARTING,
            public_port=port,
            private_port=INTERNAL_PORT,
        )

    @staticmethod
    def _build_volumes(mounts: list[VolumeMount]) -> dict:
        return {m.host: {"bind": m.container, "mode": m.mode} for m in mounts}
