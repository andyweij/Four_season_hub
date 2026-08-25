from pydantic import BaseModel, ConfigDict


class AvailableModelResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    model_key: str
    model_type: str

    size: int
    max_images: int

    is_chat_model: bool
    supports_reasoning: bool
    supports_reasoning_effort: bool
    download_status: str
    status: str

class AvailableModelsResponse(BaseModel):
    models: list[AvailableModelResponse]
    total: int
