from app.modules.llm_management.domain.enums import ModelRuntimeStatus
from app.modules.llm_management.domain.managed_model import ManagedModel
from app.modules.llm_management.schemas.available_models import AvailableModelResponse


def to_available_model_response(model: ManagedModel) -> AvailableModelResponse:
    return AvailableModelResponse(
        model_key=model.catalog.model_key,
        model_type=model.catalog.model_type,
        size=model.catalog.size,
        max_images=model.catalog.max_images,
        is_chat_model=model.catalog.is_chat_model,
        supports_reasoning=model.catalog.supports_reasoning,
        supports_reasoning_effort=model.catalog.supports_reasoning_effort,
        download_status=model.download_status,
        status=(
            model.instance.status
            if model.instance is not None
            else ModelRuntimeStatus.NOT_INSTALLED
        ),
    )