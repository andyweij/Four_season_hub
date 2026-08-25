import asyncio
import logging
import threading
import time

import docker

from app.modules.llm_management.runtimes.labels import (
    MANAGED_BY_LABEL,
    HUB_OWNER_VALUE,
)

logger = logging.getLogger("app")

RELEVANT_ACTIONS = {"start", "die", "stop", "health_status", "create", "remove"}


class DockerEventWatcher:
    def __init__(self, client: docker.DockerClient, on_event, window_seconds: float = 5.0):
        self._client = client
        self._on_event = on_event  # async callback(container_name: str)
        self._window_seconds = window_seconds
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, loop: asyncio.AbstractEventLoop):
        self._thread = threading.Thread(target=self._run, args=(loop,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()

    def _run(self, loop: asyncio.AbstractEventLoop):
        while not self._stop_flag.is_set():
            window_start = time.time()
            window_end = window_start + self._window_seconds

            try:
                for event in self._client.events(
                        decode=True,
                        since=window_start,       # 一定要給，否則會重播歷史事件
                        until=window_end,
                        filters={"label": f"{MANAGED_BY_LABEL}={HUB_OWNER_VALUE}"},
                ):
                    if self._stop_flag.is_set():
                        break

                    action = event.get("Action", "")
                    if action not in RELEVANT_ACTIONS:
                        continue

                    name = event.get("Actor", {}).get("Attributes", {}).get("name")
                    if name:
                        asyncio.run_coroutine_threadsafe(self._on_event(name), loop)

            except Exception:
                logger.exception("event watcher window failed, retrying")

        logger.info("event watcher stopped")