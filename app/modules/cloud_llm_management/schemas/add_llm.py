from pydantic import BaseModel, SecretStr
from ..domain.enums import CloudLLMProvider

class AddLLM(BaseModel):
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