import logging

from app.modules.llm_management.artifacts.base import (
    ArtifactInspector,
)
from app.modules.llm_management.domain.artifact import (
    ArtifactCheckResult,
    ArtifactStatus,
)
from app.modules.llm_management.repositories.model_catalog import (
    ModelCatalogRepository,
)


logger = logging.getLogger(__name__)


class ModelArtifactService:
    def __init__(
        self,
        model_catalog: ModelCatalogRepository,
        artifact_inspector: ArtifactInspector,
    ):
        self.model_catalog = model_catalog
        self.artifact_inspector = artifact_inspector

    async def check_all(
        self,
    ) -> list[ArtifactCheckResult]:
        models = await self.model_catalog.list_all()

        results: list[ArtifactCheckResult] = []

        # 建議循序檢查，避免多個大型目錄同時掃描磁碟
        for model in models:
            result = await self.artifact_inspector.inspect(
                model
            )

            results.append(result)

            if result.status == ArtifactStatus.COMPLETE:
                logger.info(
                    "Model artifact complete: "
                    "model=%s size=%s path=%s",
                    result.model_key,
                    result.actual_size,
                    result.artifact_path,
                )
            else:
                logger.warning(
                    "Model artifact invalid: "
                    "model=%s status=%s "
                    "expected=%s actual=%s path=%s",
                    result.model_key,
                    result.status,
                    result.expected_size,
                    result.actual_size,
                    result.artifact_path,
                )

        return results