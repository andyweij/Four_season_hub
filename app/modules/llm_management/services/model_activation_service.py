import socket
from app.modules.llm_management.runtimes.launcher_base import ModelLauncher
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)
from app.modules.llm_management.domain.model_instance import ModelInstance
import asyncio
import logging
import time

import httpx

from app.modules.llm_management.domain.enums import ModelRuntimeStatus

logger = logging.getLogger("app")


class PortAllocationError(Exception):
    pass


class ModelActivationService:
    def __init__(
            self,
            launcher: ModelLauncher,
            registry_service: ModelRegistryService,
            endpoint_host: str = "127.0.0.1",
            port_range: tuple[int, int] = (8000, 9000),
            health_check_interval_seconds: float = 5.0,
            startup_timeout_seconds: float = 1800.0,
    ):
        self._launcher = launcher
        self._registry = registry_service
        self._endpoint_host = endpoint_host
        self._port_range = port_range
        self._health_check_interval = health_check_interval_seconds
        self._startup_timeout = startup_timeout_seconds
        self._background_tasks: set[asyncio.Task] = set()  # 防止 task 被 GC 掉的關鍵

    async def run_model(self, catalog: ModelCatalogEntry, effective_config: dict) -> ModelInstance:
        port = self._allocate_port()
        instance = await self._launcher.launch(catalog, effective_config, port)

        task = asyncio.create_task(self._watch_startup(catalog.model_name, instance.public_port))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return instance  # 立刻回傳 STARTING，不等健康檢查跑完

    def _allocate_port(self) -> int:
        start, end = self._port_range
        for port in range(start, end):
            if self._is_port_free(port):
                return port
        raise PortAllocationError(f"No free port in range {start}-{end}")

    async def _watch_startup(self, model_name: str, port: int) -> None:
        url = f"http://{self._endpoint_host}:{port}/health"
        deadline = time.monotonic() + self._startup_timeout

        while time.monotonic() < deadline:
            await asyncio.sleep(self._health_check_interval)

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
            except httpx.HTTPError:
                continue  # 連不上，process 可能還在載入，繼續等

            if response.status_code == 200:
                logger.info("Model %s is ready on port %d", model_name, port)
                self._update_status(model_name, ModelRuntimeStatus.READY)
                return

            if response.status_code != 503:
                # 503 通常代表「模型還在載入中」，其他非 200 狀態視為異常，直接判定失敗、不再繼續輪詢
                logger.error(
                    "Model %s health check returned unexpected status %d, marking as failed",
                    model_name, response.status_code,
                )
                self._update_status(model_name, ModelRuntimeStatus.ERROR)
                return

        logger.error("Model %s did not become ready within %.0f seconds", model_name, self._startup_timeout)
        self._update_status(model_name, ModelRuntimeStatus.ERROR)

    def _update_status(self, model_name: str, status: ModelRuntimeStatus) -> None:
        model = self._registry.get(model_name)
        if model is not None and model.instance is not None:
            model.instance.status = status

    @staticmethod
    def _is_port_free(port: int, host: str = "127.0.0.1") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False
