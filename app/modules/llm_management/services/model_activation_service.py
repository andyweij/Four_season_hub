import socket

from app.modules.llm_management.runtimes.base import RuntimeInspector
from app.modules.llm_management.runtimes.launcher_base import ModelLauncher
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.llm_management.domain.managed_model import (
    ManagedModel
)
from app.modules.llm_management.domain.model_instance import ModelInstance
import asyncio
import logging
from app.modules.llm_management.exceptions import PortAllocationError, ModelAlreadyRunningError, \
    ModelStillLaunchingError
from app.modules.llm_management.domain.enums import ModelRuntimeStatus
from app.modules.llm_management.services.model_health_watcher import ModelHealthWatcher

logger = logging.getLogger(__name__)


class ModelActivationService:
    def __init__(
            self,
            launcher: ModelLauncher,
            registry_service: ModelRegistryService,
            runtime_inspector: RuntimeInspector,
            health_watcher: ModelHealthWatcher,
            endpoint_host: str = "127.0.0.1",
            container_prefix: str = "",
            port_range: tuple[int, int] = (8000, 8030),
    ):
        self._launcher = launcher
        self._registry = registry_service
        self._endpoint_host = endpoint_host
        self._container_prefix = container_prefix
        self._port_range = port_range
        self._health_watcher = health_watcher
        self._background_tasks: set[asyncio.Task] = set()  # 防止 task 被 GC 掉的關鍵
        self.runtime_inspector = runtime_inspector
        self._lock = asyncio.Lock()
        self._reserved_ports: set[int] = set()

    async def run_model(self, model: ManagedModel) -> ModelInstance:
        async with self._lock:
            if model.runtime_status in (ModelRuntimeStatus.STARTING, ModelRuntimeStatus.READY):
                raise ModelAlreadyRunningError(model.catalog.model_name)
            port = self._allocate_port()
            self._reserved_ports.add(port)
            model.runtime_status = ModelRuntimeStatus.STARTING

        try:
            instance = await self._launcher.launch(model.catalog, model.effective_launch_config, port)
        except Exception:
            model.runtime_status = ModelRuntimeStatus.ERROR
            self._reserved_ports.discard(port)
            raise

        model.instance = instance
        self._health_watcher.watch(model.catalog.model_name, port, self._registry.update_instance_status)
        return instance

    async def disable_model(self, model: ManagedModel) -> None:
        """
        停止並移除指定的模型實例，並更新其狀態為 STOPPED。
        """
        if model.runtime_status == ModelRuntimeStatus.STARTING and model.instance is None:
            raise ModelStillLaunchingError(model.catalog.model_name)
        if model.instance is not None:
            await self.runtime_inspector.stop_and_remove_instance(model.instance.name, model.instance.id)
            self._reserved_ports.discard(model.instance.public_port)
            model.instance = None
        model.runtime_status = ModelRuntimeStatus.STOPPED

    """
    檢查指定的 port 是否可用，若可用則回傳該 port，否則在指定的 port 範圍內尋找第一個可用的 port。若整個範圍都沒有可用的 port，則拋出 PortAllocationError。
    """

    def _allocate_port(self) -> int:
        """
        在指定的 port 範圍內尋找第一個可用的 port，並回傳該 port。
        若整個範圍都沒有可用的 port，則拋出 PortAllocationError。
        """
        start, end = self._port_range
        for port in range(start, end):
            if port in self._reserved_ports:
                continue
            if self._is_port_free(port):
                return port
        raise PortAllocationError(f"No free port in range {start}-{end}")

    @staticmethod
    def _is_port_free(port: int, host: str = "0.0.0.0") -> bool:
        """
        檢查指定的 port 是否可用，若可用則回傳 True，否則回傳 False。
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False
