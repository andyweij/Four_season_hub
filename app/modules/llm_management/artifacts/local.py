import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from app.modules.llm_management.domain.artifact import (
    ArtifactCheckResult,
    ArtifactStatus,
)
from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


class LocalArtifactInspector:
    def __init__(
        self,
        model_base_path: Path,
    ):
        self.model_base_path = model_base_path.resolve()

    async def inspect(
        self,
        model: ModelCatalogEntry,
    ) -> ArtifactCheckResult:
        return await asyncio.to_thread(
            self._inspect_sync,
            model,
        )

    def _inspect_sync(
        self,
        model: ModelCatalogEntry,
    ) -> ArtifactCheckResult:
        checked_at = datetime.now(timezone.utc)

        try:
            artifact_path = self._resolve_artifact_path(
                model.relative_path
            )

        except ValueError as error:
            return ArtifactCheckResult(
                model_key=model.model_key,
                relative_path=self.model_base_path,
                status=ArtifactStatus.INVALID_PATH,
                expected_size=model.size,
                checked_at=checked_at,
                error_message=str(error),
            )

        if not artifact_path.exists():
            return ArtifactCheckResult(
                model_key=model.model_key,
                relative_path=artifact_path,
                status=ArtifactStatus.MISSING,
                expected_size=model.size,
                actual_size=None,
                checked_at=checked_at,
            )

        try:
            actual_size = self._calculate_size(
                artifact_path
            )

        except OSError as error:
            return ArtifactCheckResult(
                model_key=model.model_key,
                relative_path=artifact_path,
                status=ArtifactStatus.ERROR,
                expected_size=model.size,
                actual_size=None,
                checked_at=checked_at,
                error_message=str(error),
            )

        if actual_size == model.size:
            status = ArtifactStatus.COMPLETE
        else:
            status = ArtifactStatus.SIZE_MISMATCH

        return ArtifactCheckResult(
            model_key=model.model_key,
            relative_path=artifact_path,
            status=status,
            expected_size=model.size,
            actual_size=actual_size,
            checked_at=checked_at,
        )

    def _resolve_artifact_path(
        self,
        artifact_name: str,
    ) -> Path:
        relative_path = Path(artifact_name)

        if relative_path.is_absolute():
            raise ValueError(
                "modelArtifact must be a relative path"
            )

        artifact_path = (
            self.model_base_path / relative_path
        ).resolve()

        if not artifact_path.is_relative_to(
            self.model_base_path
        ):
            raise ValueError(
                "modelArtifact is outside model_base_path"
            )

        return artifact_path

    def _calculate_size(
        self,
        path: Path,
    ) -> int:
        if path.is_file():
            return path.stat().st_size

        if not path.is_dir():
            raise OSError(
                f"Unsupported artifact type: {path}"
            )

        total_size = 0
        pending_directories = [path]

        while pending_directories:
            current_directory = pending_directories.pop()

            with os.scandir(current_directory) as entries:
                for entry in entries:
                    # 避免 Symbolic Link 循環或離開模型根目錄
                    if entry.is_symlink():
                        continue

                    if entry.is_file(
                        follow_symlinks=False
                    ):
                        total_size += entry.stat(
                            follow_symlinks=False
                        ).st_size

                    elif entry.is_dir(
                        follow_symlinks=False
                    ):
                        pending_directories.append(
                            Path(entry.path)
                        )

        return total_size