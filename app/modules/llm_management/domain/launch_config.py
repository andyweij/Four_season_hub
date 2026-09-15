from typing import Any
from pydantic import BaseModel
from app.modules.llm_management.domain.volume_mount import VolumeMount


class DockerLaunchConfig(BaseModel):
    volumes: list[VolumeMount] = []


class LaunchConfig(BaseModel):
    args: dict[str, Any] = {}
    env: list[str] = []
    container: DockerLaunchConfig | None = None