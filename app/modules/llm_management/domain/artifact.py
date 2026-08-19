from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class ArtifactStatus(StrEnum):
    COMPLETE = "complete"
    MISSING = "missing"
    SIZE_MISMATCH = "size_mismatch"
    INVALID_PATH = "invalid_path"
    ERROR = "error"


class ArtifactCheckResult(BaseModel):
    model_key: str
    artifact_path: Path

    status: ArtifactStatus

    expected_size: int
    actual_size: int | None = None

    checked_at: datetime
    error_message: str | None = None