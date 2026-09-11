import logging
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.chat.repositories.conversation_repository import ConversationRepository
from app.modules.chat.repositories.message_repository import MessageRepository
from app.modules.chat.services.conversation_service import ConversationService
from app.modules.llm_management.domain.managed_model import ManagedModel
from app.modules.chat.schemas.chat_request import ChatRequest
from app.modules.llm_management.domain.enums import ModelRuntimeStatus

logger = logging.getLogger("app")

from app.modules.llm_inference.services.payload_builder import build_chat_payload


class ChatStreamService:
    def __init__(
            self,
            registry_service: ModelRegistryService,
            conversation_service=ConversationService,
            message_repository=MessageRepository,
            inference_client=InferenceClient,
            conversation_repository=ConversationRepository
    ):
        self._registry_service = registry_service
        self._conversation_service = conversation_service
        self._message_repository = message_repository
        self._inference_client = inference_client
        self._conversation_repository = conversation_repository

    def _pre_check(self, model: ManagedModel) -> bool:
        pre_check: bool = True
        if model & model.instance is not None:
            if model.instance.status is not ModelRuntimeStatus.READY:
                pre_check = False
        else:
            pre_check = False
        return pre_check

    async def chat_stream(self, request: ChatRequest):
        model_name = request.model
        messages = request.message
        parameters = request.parameters
        model = self._registry_service.get(model_name)
        if self._pre_check(model):
            model_type = model.catalog.model_type
            payload = build_chat_payload(model_type, model_name, messages, parameters)
