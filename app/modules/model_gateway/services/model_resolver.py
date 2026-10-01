from app.modules.cloud_llm_management.domain.endpoints import provider_base_url
from app.modules.model_gateway.domain.model_target import ModelCapabilities, ModelTarget
from app.modules.model_gateway.exceptions import (
    ModelNotFoundError, ModelNotReadyError, ModelNotChatCapableError, ModelSourceNotImplementedError,
)


class ModelResolver:
    def __init__(self, registry_service, cloud_repository=None):
        self.registry = registry_service
        self.cloud = cloud_repository

    async def resolve(self, model_ref):
        if model_ref.source == "local":
            model = self.registry.get(model_ref.id)
            if model is None:
                raise ModelNotFoundError("Model was not found.")
            if not model.catalog.is_chat_model:
                raise ModelNotChatCapableError("Model does not support chat.")
            ready = self.registry.get_ready_chat_model(model_ref.id)
            if ready is None:
                raise ModelNotReadyError("Model is not ready.")
            catalog = ready.model.catalog
            return ModelTarget(
                source="local", id=model_ref.id, model_name=catalog.model_name,
                provider="openai_compatible", base_url=f"{ready.endpoint.rstrip('/')}/v1",
                capabilities=ModelCapabilities(
                    streaming=catalog.supports_streaming, tool_calling=catalog.supports_tool_calling,
                    reasoning=catalog.supports_reasoning, reasoning_effort=catalog.supports_reasoning_effort,
                ),
                max_context_tokens=ready.model.context_len if ready.model.context_len > 0 else None,
            )
        if self.cloud is None:
            raise ModelSourceNotImplementedError("Cloud repository is unavailable.")
        connection = await self.cloud.get_by_id(model_ref.id)
        if connection is None:
            raise ModelNotFoundError("Cloud connection was not found.")
        if not connection.enabled or connection.status == "disabled":
            raise ModelNotReadyError("Cloud connection is disabled.")
        if not connection.is_chat_model:
            raise ModelNotChatCapableError("Model does not support chat.")
        provider = connection.provider.value
        base_url = provider_base_url(provider, connection.base_url)
        return ModelTarget(
            source="cloud", id=connection.id, model_name=connection.model_name,
            provider=provider, base_url=base_url.rstrip("/"),
            capabilities=ModelCapabilities(
                streaming=connection.capabilities.streaming,
                tool_calling=connection.capabilities.tool_calling,
                reasoning=connection.capabilities.reasoning,
                reasoning_effort=connection.capabilities.reasoning_effort,
            ),
            max_context_tokens=connection.max_model_len if connection.max_model_len > 0 else None,
            credential_ref=connection.id,
        )
