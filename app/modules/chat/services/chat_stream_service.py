import logging
import asyncio
from app.modules.chat.domain.enums import ChatEventType, ChatContentType, MessageRole
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.chat.services.conversation_service import ConversationService
from app.modules.chat.services.inference_mapper import to_inference_message
from app.modules.chat.schemas.chat_request import ChatRequest, ChatMessage, ChatContent
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
        self._background_tasks: set[asyncio.Task] = set()

    async def chat_stream(self, request: ChatRequest, user_id: str):
        model_name = request.model
        parameters = request.parameters
        conversation_id = request.conversation_id
        finish_reason: str | None = None
        usage: dict | None = None
        ready = self._registry_service.get_ready_chat_model(model_name)
        if ready is None:
            yield ChatStreamEvent(type=ChatEventType.ERROR, content="模型目前無法使用")
            return
        endpoint_url = ready.endpoint  # str，型別檢查器完全滿意，不需要再檢查一次
        model_type = ready.model.catalog.model_type
        message, = request.messages
        user_messages = to_inference_message(message)

        inference_request = InferenceRequest(
            model=model_name,
            messages=[user_messages],
            temperature=parameters.temperature,
            top_p=parameters.top_p,
            max_tokens=parameters.max_tokens,
            reasoning_effort=request.reasoning_effort,
            model_type=model_type
        )
        if conversation_id:
            conversation = await self._conversation_service.get_conversation_by_id(conversation_id, user_id)
            if conversation.model != model_name:
                yield ChatStreamEvent(type=ChatEventType.ERROR, content="模型不匹配")
                return
            question_message = await self._conversation_service.add_user_message(
                conversation_id=conversation.id,
                user_id=user_id,
                inference_message=message
            )
            yield ChatStreamEvent(
                type=ChatEventType.ACK,
                conversation_id=conversation.id,
                user_message_id=question_message.id,
            )
        else:
            result = await self._conversation_service.create_conversation(
                user_id=user_id,
                model_name=model_name,
                inference_message=message,
                title=""
            )
            if result is None:
                yield ChatStreamEvent(type=ChatEventType.ERROR, conversation_id="", content="建立對話失敗")
                return
            conversation, question_message = result

        task = asyncio.create_task(
            self.generate_title(conversation_id=conversation.id, user_id=user_id, user_message=message))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        yield ChatStreamEvent(
            type=ChatEventType.ACK,
            conversation_id=conversation.id,
            user_message_id=question_message.id,
        )

        accumulated = []
        reasoning_content = []
        async for delta in self._inference_client.stream_chat_completion(endpoint_url, inference_request):
            if delta.reasoning_content:
                reasoning_content.append(delta.reasoning_content)
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
        await self._conversation_service.add_assistant_message(
            conversation_id=conversation.id,
            user_id=user_id,
            inference_message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=[ChatContent(type=ChatContentType.TEXT, text="".join(accumulated))],
            ),
            finish_reason=finish_reason,
            usage=usage,
        )

        yield ChatStreamEvent(
            type=ChatEventType.DONE,
            conversation_id=conversation.id,
            finish_reason=finish_reason,
            usage=usage,
        )

    async def generate_title(self, conversation_id: str, user_id: str, user_message: ChatMessage):
        """
        英文:
        Generate a title for the conversation by sending a system message to the model.
        中文:
        透過向模型發送系統訊息，為對話生成標題。
        """
        conversation = await self._conversation_service.get_conversation_by_id(conversation_id, user_id)
        if conversation.user_id != user_id:
            logger.error("無權限存取此對話")
            return
        model_name = conversation.model
        ready = self._registry_service.get_ready_chat_model(model_name)
        if ready is None:
            logger.error(f"{model_name}:此模型目前無法使用")
            return
        endpoint_url = ready.endpoint  # str，型別檢查器完全滿意，不需要再檢查一次
        model_type = ready.model.catalog.model_type

        inference_request = InferenceRequest(
            model=model_name,
            messages=[to_inference_message(ChatMessage(
                role=MessageRole.SYSTEM,
                content=[ChatContent(type=ChatContentType.TEXT, text="請為這段對話生成一個簡短的標題")]
            )), to_inference_message(user_message)],
            temperature=0.5,
            top_p=1.0,
            max_tokens=500,
            model_type=model_type
        )

        generate_result = await self._inference_client.not_stream_chat_completion(endpoint_url, inference_request)

        title = generate_result.content.strip()

        await self._conversation_service.update_conversation_title(conversation_id, user_id, title)
