from typing import Protocol

from app.modules.llm_management.domain.artifact import (
    ArtifactCheckResult,
)
from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


class ArtifactInspector(Protocol):
    async def inspect(
        self,
        model: ModelCatalogEntry,
    ) -> ArtifactCheckResult:
        ...