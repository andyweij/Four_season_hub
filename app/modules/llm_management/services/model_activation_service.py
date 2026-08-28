import socket
from app.modules.llm_management.runtimes.launcher_base import ModelLauncher
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)
from app.modules.llm_management.domain.model_instance import ModelInstance


class PortAllocationError(Exception):
    pass


class ModelActivationService:
    def __init__(
            self,
            launcher: ModelLauncher,  # 依 RuntimeType 注入 Docker 或 Native 版本
            registry_service: ModelRegistryService,
            port_range: tuple[int, int] = (8000, 9000),
    ):
        self._launcher = launcher
        self._registry = registry_service
        self._port_range = port_range

    async def run_model(self, catalog: ModelCatalogEntry, effective_config: dict) -> ModelInstance:
        port = self._allocate_port()
        return await self._launcher.launch(catalog, effective_config, port)

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
