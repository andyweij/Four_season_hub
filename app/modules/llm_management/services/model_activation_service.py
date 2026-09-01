import socket

from app.modules.llm_management.runtimes.base import RuntimeInspector
from app.modules.llm_management.runtimes.launcher_base import ModelLauncher
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)
from app.modules.llm_management.domain.model_instance import ModelInstance
import asyncio
import logging
from app.modules.llm_management.domain.enums import ModelRuntimeStatus
from app.modules.llm_management.exceptions import PortAllocationError
from app.modules.llm_management.services.model_health_watcher import ModelHealthWatcher
from app.modules.llm_management.domain.launch_config import LaunchConfig

logger = logging.getLogger("app")


class ModelActivationService:
    def __init__(
            self,
            launcher: ModelLauncher,
            registry_service: ModelRegistryService,
            runtime_inspector: RuntimeInspector,
            health_watcher: ModelHealthWatcher,
            endpoint_host: str = "127.0.0.1",
            port_range: tuple[int, int] = (8000, 8030),
    ):
        self._launcher = launcher
        self._registry = registry_service
        self._endpoint_host = endpoint_host
        self._port_range = port_range
        self._health_watcher = health_watcher
        self._background_tasks: set[asyncio.Task] = set()  # 防止 task 被 GC 掉的關鍵
        self.runtime_inspector = runtime_inspector

    async def run_model(self, catalog: ModelCatalogEntry, effective_config: LaunchConfig) -> ModelInstance:
        port = self._allocate_port()
        instance = await self._launcher.launch(catalog, effective_config, port)
        self._health_watcher.watch(catalog.model_name, port, self._registry.update_instance_status)
        return instance  # 立刻回傳 STARTING，不等健康檢查跑完

    async def disable_model(self, instance: ModelInstance) -> None:
        await self.runtime_inspector.stop_and_remove_instance(instance.id)
        self._registry.update_instance_status(instance.name, ModelRuntimeStatus.STOPPED)

    """
    檢查指定的 port 是否可用，若可用則回傳該 port，否則在指定的 port 範圍內尋找第一個可用的 port。若整個範圍都沒有可用的 port，則拋出 PortAllocationError。
    """

    def _allocate_port(self) -> int:
        start, end = self._port_range
        for port in range(start, end):
            if self._is_port_free(port):
                return port
        raise PortAllocationError(f"No free port in range {start}-{end}")

    @staticmethod
    def _is_port_free(port: int, host: str = "127.0.0.1") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False
