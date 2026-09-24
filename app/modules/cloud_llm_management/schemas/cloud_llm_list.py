from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CloudLLMList(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,  # 序列化為 JSON 時自動轉為 camelCase (model_name -> modelName)
        populate_by_name=True
    )
    model_name: str
    max_images: int
    max_model_len: int
    support_image: bool
    is_chat_model: bool
    supports_reasoning: bool
    supports_reasoning_effort: bool