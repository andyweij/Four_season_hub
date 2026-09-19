# runtimes/native_launcher.py
import asyncio
import logging
import subprocess
from pathlib import Path

from app.modules.llm_management.domain.enums import ComponentType, ModelRuntimeStatus
from app.modules.llm_management.domain.model_instance import ModelInstance
from app.modules.llm_management.domain.models import ModelCatalogEntry
from app.modules.llm_management.runtimes.launch_args import build_config_args, parse_env_list
from app.modules.llm_management.domain.launch_config import LaunchConfig
import os

logger = logging.getLogger("app")

MODEL_PATH_FLAG = "-m"
PORT_FLAG = "--port"
NAME_FLAG = "--alias"
BOOLEAN_FLAGS_KEY = "boolean"


class NativeModelLauncher:
    def __init__(
            self,
            model_base_path: Path,
            model_engine_path: Path,
            log_dir: Path = Path("logs/native"),
    ):
        self.model_base_path = model_base_path
        self.model_engine_path = model_engine_path
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def launch(self, catalog: ModelCatalogEntry, effective_config: LaunchConfig, port: int) -> ModelInstance:
        return await asyncio.to_thread(self._launch_sync, catalog, effective_config, port)

    def _launch_sync(self, catalog: ModelCatalogEntry, effective_config: LaunchConfig, port: int) -> ModelInstance:
        model_path = self._resolve_model_path(catalog)
        executable = self.model_engine_path / "llama-server.exe"
        cmdline = [
            str(executable),
            MODEL_PATH_FLAG, str(model_path),
            PORT_FLAG, str(port),
            NAME_FLAG, catalog.model_name,
            *build_config_args(effective_config.args),
        ]

        log_path = self.log_dir / f"{catalog.model_name}.log"
        log_file = open(log_path, "ab")

        logger.info("Launching native model: %s", " ".join(cmdline))
        env = effective_config.env
        process = subprocess.Popen(
            cmdline,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,  # 建議一併加上，理由見下
            cwd=str(self.model_engine_path),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            env={**os.environ, **parse_env_list(env)} if env else None,
        )

        return ModelInstance(
            id=str(process.pid),
            name=catalog.model_name,
            component=ComponentType.MODEL,
            status=ModelRuntimeStatus.STARTING,
            public_port=port,
            private_port=port,
        )

    def _resolve_model_path(self, catalog: ModelCatalogEntry) -> Path:
        base = self.model_base_path / catalog.relative_path
        if catalog.entry_point:
            return base / catalog.entry_point
        return base
