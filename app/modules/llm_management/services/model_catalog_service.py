from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)
from app.modules.llm_management.repositories.model_catalog import (
    ModelCatalogRepository,
)
import logging

logger = logging.getLogger("app")


class ModelCatalogService:
    def __init__(
            self,
            repository: ModelCatalogRepository,
    ):
        self.repository = repository

    async def list_models(
            self,
    ) -> list[ModelCatalogEntry]:
        models = await self.repository.list_all()

        logger.info("Retrieved %d models from the catalog", len(models))
        return [
            model
            for model in models
        ]
