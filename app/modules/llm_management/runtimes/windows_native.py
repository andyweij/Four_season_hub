import asyncio
from pathlib import Path

import httpx
import psutil

from app.modules.llm_management.domain.model_instance import (
    ComponentType, ModelInstance, ModelRuntimeStatus,
)
import logging

logger = logging.getLogger("app")
HEALTH_CHECK_TIMEOUT_SECONDS = 2.0
MODEL_PATH_FLAGS = ("-m", "--model")
NAME_FLAG = "--alias"
PORT_FLAG = "--port"
PROCESS_NAME = "llama-server.exe"


class WindowsNativeRuntimeInspector:
    def __init__(self, model_base_path: Path, health_host: str = "127.0.0.1"):
        self.model_base_path = model_base_path.resolve()
        self.health_host = health_host

    async def get_status(self, container_name: str) -> ModelRuntimeStatus:
        instance = await self.get_instance(container_name)
        if instance is None:
            return ModelRuntimeStatus.NOT_INSTALLED
        return instance.status

    async def list_running_instances(self, component: ComponentType | None = None) -> list[ModelInstance]:
        proc_infos = await asyncio.to_thread(self._find_model_processes_sync)
        instances = [
            instance
            for instance in await asyncio.gather(*(self._build_instance(info) for info in proc_infos))
            if instance is not None
        ]
        logger.info(f"Found {len(instances)} running instances.")
        if component is not None:
            instances = [instance for instance in instances if instance.component == component]
        return instances

    async def get_instance(self, container_name: str) -> ModelInstance | None:
        proc_infos = await asyncio.to_thread(self._find_model_processes_sync)
        for info in proc_infos:
            if self._extract_name(info["cmdline"]) == container_name:
                return await self._build_instance(info)
        return None

    async def stop_and_remove_instance(self, instance_id: str) -> None:
        try:
            proc = psutil.Process(int(instance_id))
            proc.terminate()
            proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            logger.warning(f"Failed to terminate process {instance_id}. It may have already exited.")

    def _find_model_processes_sync(self) -> list[dict]:
        model_base = str(self.model_base_path).lower()
        matches = []
        for proc in psutil.process_iter(["pid", "name", "cmdline", "status"]):
            try:
                info = proc.info
                if info.get("name") != PROCESS_NAME:
                    continue
                cmdline = info.get("cmdline") or []
                if any(model_base in arg.lower() for arg in cmdline):
                    matches.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return matches

    @staticmethod
    def _extract_arg_value(cmdline: list[str], *flags: str) -> str | None:
        for index, arg in enumerate(cmdline):
            if arg in flags and index + 1 < len(cmdline):
                return cmdline[index + 1]
            for flag in flags:
                if arg.startswith(f"{flag}="):
                    return arg.split("=", 1)[1]
        return None

    def _extract_name(self, cmdline: list[str]) -> str | None:
        alias = self._extract_arg_value(cmdline, NAME_FLAG)
        if alias:
            return alias

        model_path = self._extract_arg_value(cmdline, *MODEL_PATH_FLAGS)
        if model_path is None:
            return None
        try:
            relative = Path(model_path).resolve().relative_to(self.model_base_path)
        except ValueError:
            return None
        return relative.parts[0] if relative.parts else None

    async def _build_instance(self, proc_info: dict) -> ModelInstance | None:
        cmdline = proc_info.get("cmdline") or []
        name = self._extract_name(cmdline)
        if name is None:
            return None

        port_value = self._extract_arg_value(cmdline, PORT_FLAG)
        port = int(port_value) if port_value and port_value.isdigit() else 0

        status = await self._probe_status(proc_info["status"], port)
        return ModelInstance(
            id=str(proc_info["pid"]),
            name=name,
            component=ComponentType.MODEL,
            status=status,
            public_port=port,
            private_port=port,
        )

    async def _probe_status(self, process_status: str, port: int) -> ModelRuntimeStatus:
        if process_status == psutil.STATUS_ZOMBIE:
            return ModelRuntimeStatus.ERROR
        if port == 0:
            return ModelRuntimeStatus.UNKNOWN

        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT_SECONDS) as client:
                response = await client.get(f"http://{self.health_host}:{port}/health")
        except httpx.HTTPError:
            return ModelRuntimeStatus.STARTING

        return ModelRuntimeStatus.READY if response.status_code == 200 else ModelRuntimeStatus.UNHEALTHY
