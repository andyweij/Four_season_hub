from typing import Any
from pydantic import BaseModel, ConfigDict


class UpdateLaunchConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_name: str
    config_overrides: dict[str, Any]