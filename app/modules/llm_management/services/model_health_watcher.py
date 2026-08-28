import asyncio
import logging
import time
from typing import Callable

import httpx

from app.modules.llm_management.domain.enums import ModelRuntimeStatus

logger = logging.getLogger("app")

StatusCallback = Callable[[str, ModelRuntimeStatus], None]


class ModelHealthWatcher:
    def __init__(
            self,
            endpoint_host: str = "127.0.0.1",
            health_check_interval_seconds: float = 5.0,
            startup_timeout_seconds: float = 1800.0,
    ):
        self._endpoint_host = endpoint_host
        self._health_check_interval = health_check_interval_seconds
        self._startup_timeout = startup_timeout_seconds
        self._background_tasks: set[asyncio.Task] = set()

    def watch(self, model_name: str, port: int, on_status_change: StatusCallback) -> None:
        task = asyncio.create_task(self._watch_loop(model_name, port, on_status_change))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _watch_loop(self, model_name: str, port: int, on_status_change: StatusCallback) -> None:
        url = f"http://{self._endpoint_host}:{port}/health"
        deadline = time.monotonic() + self._startup_timeout

        while time.monotonic() < deadline:
            await asyncio.sleep(self._health_check_interval)

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
            except httpx.HTTPError:
                continue

            if response.status_code == 200:
                logger.info("Model %s is ready on port %d", model_name, port)
                on_status_change(model_name, ModelRuntimeStatus.READY)
                return

            if response.status_code != 503:
                logger.error(
                    "Model %s health check returned unexpected status %d, marking as failed",
                    model_name, response.status_code,
                )
                on_status_change(model_name, ModelRuntimeStatus.ERROR)
                return

        logger.error("Model %s did not become ready within %.0f seconds", model_name, self._startup_timeout)
        on_status_change(model_name, ModelRuntimeStatus.ERROR)
