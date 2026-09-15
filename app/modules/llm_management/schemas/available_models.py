from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AvailableModelResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,  # 序列化為 JSON 時自動轉為 camelCase (model_name -> modelName)
        populate_by_name=True
    )

    model_name: str
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
