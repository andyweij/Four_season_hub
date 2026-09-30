from pydantic import BaseModel, SecretStr, ConfigDict
from pydantic.alias_generators import to_camel

from ..domain.enums import CloudLLMProvider


class AddLLM(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid", )
    name: str
    provider: CloudLLMProvider
    model_name: str
    base_url: str | None = None
    api_key: SecretStr

    max_images: int = 0
    max_model_len: int = -1
    is_chat_model: bool = True
    supports_reasoning: bool = False
    supports_reasoning_effort: bool = False
    supports_tool_calling: bool = False
