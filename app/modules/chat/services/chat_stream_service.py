import logging
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.chat.repositories.conversation_repository import ConversationRepository
from app.modules.chat.repositories.message_repository import MessageRepository
from app.modules.chat.services.conversation_service import ConversationService
from app.modules.llm_management.domain.managed_model import ManagedModel
from app.modules.chat.schemas.chat_request import ChatRequest
from app.modules.llm_management.domain.enums import ModelRuntimeStatus
from app.modules.llm_inference.domain.inference_request import InferenceRequest, InferenceMessage
from app.modules.chat.domain.chat_stream_event import ChatStreamEvent

logger = logging.getLogger("app")


class ChatStreamService:
    def __init__(
            self,
            registry_service: ModelRegistryService,
            conversation_service: ConversationService,
            inference_client: InferenceClient,
    ):
        self._registry_service = registry_service
        self._conversation_service = conversation_service
        self._inference_client = inference_client

    async def chat_stream(self, request: ChatRequest, user_id: str):
        model_name = request.model
        parameters = request.parameters
        model = self._registry_service.get(model_name)
        if model is not None and self._pre_check(model):
            inference_request = InferenceRequest(
                model=model_name,
                messages=[
                    InferenceMessage(role=m.role, content=m.content)
                    for m in request.message
                ],
                temperature=parameters.temperature, top_p=parameters.top_p,
                max_tokens=parameters.max_tokens,
                reasoning_effort=request.reasoning_effort,
                model_type=model.catalog.model_type
            )
            result = await self._conversation_service.create_conversation(
                user_id=user_id,
                model_name=model_name,
                inference_message=InferenceMessage(role=request.message[0].role, content=request.message[0].content),
                title=""
            )
            if result is not None:
                conversation, user_message = result

            yield ChatStreamEvent(
                type="ack",
                conversation_id=conversation.id,
                user_message_id=user_message.id,
            )
            endpoint_url = model.endpoint
            accumulated = []
            async for delta in self._inference_client.stream_chat_completion(endpoint_url, inference_request):
                if delta.content:
                    accumulated.append(delta.content)
                    yield ChatStreamEvent(
                        type="delta",
                        conversation_id=conversation.id,
                        content=delta.content,
                    )

            # 存 assistant message 之後
            yield ChatStreamEvent(
                type="done",
                conversation_id=conversation.id,
                finish_reason=...,
                usage=...,
            )

    @staticmethod
    def _pre_check(model: ManagedModel) -> bool:
        if model.instance is None:
            return False
        if model.endpoint is None:
            return False
        return model.instance.status == ModelRuntimeStatus.READY
