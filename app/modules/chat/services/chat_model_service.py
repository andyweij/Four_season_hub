from app.modules.llm_management.services.model_registry_service import ModelRegistryService


class ChatModelService:
    def __init__(self,
                 registry_service: ModelRegistryService
                 ):
        self.registry_service = registry_service

    async def get_models(self) -> list[str]:
        """取得所有模型資訊"""
        return self.registry_service.get_all_runnings()
