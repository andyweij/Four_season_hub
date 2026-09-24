from app.modules.llm_management.services.model_registry_service import ModelRegistryService
import logging

logger = logging.getLogger(__name__)


class ChatModelService:
    def __init__(self,
                 registry_service: ModelRegistryService
                 ):
        self.registry_service = registry_service

    async def get_models(self) -> list[str]:
        logger.info("Listing ready chat models")

        models = self.registry_service.get_all_running_instances()

        logger.info("Ready chat models retrieved count=%d", len(models))
        return models
