import asyncio
import logging
from uuid import uuid4
from app.modules.chat.domain.enums import ChatEventType, ChatContentType, MessageRole, MessageStatus
from app.modules.chat.domain.chat_stream_event import ChatStreamEvent
from app.modules.chat.schemas.chat_request import ChatMessage, ChatContent
from app.modules.chat.services.inference_mapper import to_inference_message
from app.modules.llm_inference.domain.inference_request import InferenceRequest
from app.modules.agent_execution.schemas.task_request import AgentTaskRequest
from app.modules.model_gateway.schemas.completion_request import CompletionRequest
from app.modules.agent_execution.schemas.execution_request import ModelRef

logger = logging.getLogger(__name__)


class ChatStreamService:
    def __init__(self, registry_service, conversation_service, inference_client, agent_services=None):
        self._registry_service = registry_service
        self._conversation_service = conversation_service
        self._inference_client = inference_client
        self._agents = agent_services

    async def chat_stream(self, request, user_id):
        message = request.messages[0]
        if message.role != MessageRole.USER:
            raise ValueError("Only user messages may be submitted.")
        if request.model_ref and request.model and (
            request.model_ref.source != "local" or request.model_ref.id != request.model
        ):
            raise ValueError("model and modelRef conflict.")
        model_ref = request.model_ref or (ModelRef(source="local", id=request.model) if request.model else None)
        if not request.agent_id and model_ref is None:
            raise ValueError("A model must be selected.")
        if request.agent_id and any(part.type != ChatContentType.TEXT for part in message.content):
            raise ValueError("Agent v1 accepts text only.")
        supported_parameters = request.parameters.model_dump(include={"temperature", "top_p", "max_tokens"})
        if (request.agent_id or (model_ref and model_ref.source == "cloud")) and (
            request.parameters.top_k is not None or request.parameters.seed is not None
            or request.parameters.extra_parameters
        ):
            raise ValueError("Agent/cloud gateway does not support these generation parameters.")
        model_name = (model_ref.id if model_ref and model_ref.source == "local"
                      else f"cloud:{model_ref.id}" if model_ref else f"agent:{request.agent_id}")
        if request.conversation_id:
            conversation = await self._conversation_service.get_conversation_by_id(request.conversation_id, user_id)
            if conversation.model != model_name or conversation.agent_id != request.agent_id:
                raise ValueError("Conversation model or Agent differs; create a new conversation.")
            question = await self._conversation_service.add_user_message(conversation.id, user_id, message)
        else:
            result = await self._conversation_service.create_conversation(
                user_id, model_name, message, message.extract_text()[:60],
                agent_id=request.agent_id,
                model_ref=model_ref.model_dump() if model_ref else None,
            )
            if result is None:
                raise ValueError("Conversation could not be created.")
            conversation, question = result
        history = await self._conversation_service.get_message_list(conversation.id, user_id)
        history = [m for m in history if m.status == MessageStatus.COMPLETE and m.role in {MessageRole.USER, MessageRole.ASSISTANT}]
        # Keep complete stored messages in order, within a conservative char budget.
        selected, size = [], 0
        for item in reversed(history[-40:]):
            text = "".join(p.text for p in item.content)
            if not text and item.id != question.id:
                continue
            if size + len(text) > 120_000:
                if not selected:
                    raise ValueError("Message exceeds the conversation size limit.")
                break
            selected.append({"role": item.role.value, "content": text})
            size += len(text)
        selected.reverse()
        accumulated, sources = [], []
        finish_reason, usage, run_id, agent_version = None, None, None, None
        status = MessageStatus.ERROR
        definition, task = None, None
        if request.agent_id:
            run_id = f"run_{uuid4().hex}"
            task = AgentTaskRequest(
                run_id=run_id, agent_id=request.agent_id, model_ref=model_ref,
                messages=selected,
                parameters=supported_parameters if request.parameters_supplied else None,
                options=request.agent_options,
            )
            definition, task = await self._agents.runs.prepare(task, user_id)
            agent_version = definition.version
        yield ChatStreamEvent(type=ChatEventType.ACK, conversation_id=conversation.id,
                              user_message_id=question.id, run_id=run_id)
        assistant = None
        try:
            if task:
                async for event in self._agents.runs.stream_prepared(definition, task):
                    base = {"conversation_id": conversation.id, "run_id": run_id}
                    if event.type == "text_delta":
                        accumulated.append(event.content)
                        yield ChatStreamEvent(type=ChatEventType.DELTA, content=event.content, **base)
                    elif event.type == "reasoning_delta":
                        yield ChatStreamEvent(type=ChatEventType.THINKING_DELTA, content=event.content, **base)
                    elif event.type == "sources":
                        sources = [s.model_dump() for s in event.sources]
                        yield ChatStreamEvent(type=ChatEventType.SOURCES, sources=sources, **base)
                    elif event.type == "progress":
                        yield ChatStreamEvent(type=ChatEventType.AGENT_PROGRESS, content=event.message, stage=event.stage, **base)
                    elif event.type == "started":
                        yield ChatStreamEvent(type=ChatEventType.AGENT_STARTED, **base)
                    elif event.type == "completed":
                        finish_reason = event.finish_reason
                        usage = event.total_usage.model_dump() if event.total_usage else event.usage.model_dump() if event.usage else None
                        status = MessageStatus.COMPLETE
                    elif event.type == "failed":
                        yield ChatStreamEvent(type=ChatEventType.ERROR, content=event.message, **base)
                    elif event.type == "cancelled":
                        status = MessageStatus.CANCELLED
                        yield ChatStreamEvent(type=ChatEventType.CANCELLED, **base)
            elif model_ref.source == "local":
                ready = self._registry_service.get_ready_chat_model(model_ref.id)
                if ready is None:
                    raise ValueError("Model is not ready.")
                inference = InferenceRequest(
                    model=model_ref.id,
                    messages=[to_inference_message(ChatMessage(
                        role=item["role"], content=[ChatContent(text=item["content"])],
                    )) for item in selected],
                    **supported_parameters,
                    reasoning_effort=request.reasoning_effort,
                    model_type=ready.model.catalog.model_type,
                )
                # Preserve the current multimodal message on the ordinary local path.
                if inference.messages:
                    inference.messages[-1] = to_inference_message(message)
                async for delta in self._inference_client.stream_chat_completion(ready.endpoint, inference):
                    if delta.content:
                        accumulated.append(delta.content)
                        yield ChatStreamEvent(type=ChatEventType.DELTA, content=delta.content, conversation_id=conversation.id)
                    if delta.reasoning_content:
                        yield ChatStreamEvent(type=ChatEventType.THINKING_DELTA, content=delta.reasoning_content, conversation_id=conversation.id)
                    finish_reason = delta.finish_reason or finish_reason
                    usage = delta.usage or usage
                if not finish_reason:
                    raise ValueError("Model stream ended without completion.")
                status = MessageStatus.COMPLETE
            else:
                if any(part.type != ChatContentType.TEXT for part in message.content):
                    raise ValueError("Cloud gateway v1 accepts text only.")
                completion = CompletionRequest(
                    run_id=f"chat_{uuid4().hex}", model_ref=model_ref, messages=selected,
                    parameters=supported_parameters,
                )
                async for event in self._agents.gateway.stream(completion):
                    if event.type == "content_delta":
                        accumulated.append(event.content)
                        yield ChatStreamEvent(type=ChatEventType.DELTA, content=event.content, conversation_id=conversation.id)
                    elif event.type == "reasoning_delta":
                        yield ChatStreamEvent(type=ChatEventType.THINKING_DELTA, content=event.content, conversation_id=conversation.id)
                    elif event.type == "completed":
                        finish_reason, usage = event.finish_reason, event.usage.model_dump() if event.usage else None
                        status = MessageStatus.COMPLETE
        finally:
            assistant = await asyncio.shield(self._conversation_service.add_assistant_message(
                conversation.id, user_id,
                ChatMessage(role=MessageRole.ASSISTANT, content=[ChatContent(text="".join(accumulated))]),
                finish_reason, usage, sources=sources, run_id=run_id,
                agent_id=request.agent_id, agent_version=agent_version, status=status,
            ))
        if status == MessageStatus.COMPLETE:
            yield ChatStreamEvent(type=ChatEventType.DONE, conversation_id=conversation.id,
                                  assistant_message_id=assistant.id, run_id=run_id,
                                  finish_reason=finish_reason, usage=usage)
