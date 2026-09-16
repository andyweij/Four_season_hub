import logging

from app.modules.chat.domain.enums import ChatEventType
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.chat.services.conversation_service import ConversationService
from app.modules.chat.services.inference_mapper import to_inference_message
from app.modules.chat.schemas.chat_request import ChatRequest
from app.modules.llm_inference.domain.inference_request import InferenceRequest
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
        if model is not None and self._pre_check(model_name):
            user_messages = to_inference_message(request.messages[0])
            message = request.messages[-1]
            inference_request = InferenceRequest(
                model=model_name,
                messages=[user_messages],
                temperature=parameters.temperature, top_p=parameters.top_p,
                max_tokens=parameters.max_tokens,
                reasoning_effort=request.reasoning_effort,
                model_type=model.catalog.model_type
            )
            result = await self._conversation_service.create_conversation(
                user_id=user_id,
                model_name=model_name,
                inference_message=message,
                title=""
            )
            if result is not None:
                conversation, user_message = result

            yield ChatStreamEvent(
                type=ChatEventType.ACK,
                conversation_id=conversation.id,
                user_message_id=user_message.id,
            )
            endpoint_url = model.endpoint
            accumulated = []
            async for delta in self._inference_client.stream_chat_completion(endpoint_url, inference_request):
                if delta.reasoning_content:
                    yield ChatStreamEvent(
                        type=ChatEventType.THINKING_DELTA,
                        conversation_id=conversation.id,
                        content=delta.reasoning_content,
                    )
                if delta.content:
                    accumulated.append(delta.content)
                    yield ChatStreamEvent(
                        type=ChatEventType.DELTA,
                        conversation_id=conversation.id,
                        content=delta.content,
                    )
                if delta.finish_reason:
                    finish_reason = delta.finish_reason
                if delta.usage:
                    usage = delta.usage
            # 存 assistant message 之後
            yield ChatStreamEvent(
                type=ChatEventType.DONE,
                conversation_id=conversation.id,
                finish_reason=finish_reason,
                usage=usage,
            )

    def _pre_check(self, model_name: str) -> bool:
        return self._registry_service.pre_check(model_name)
