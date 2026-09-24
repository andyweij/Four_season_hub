from pydantic import BaseModel
from ..domain.enums import CloudLLMProvider, CloudLLMStatus

class CloudLLMResponse(BaseModel):
    id: str
    name: str
    provider: CloudLLMProvider
    model_name: str

    enabled: bool
    status: CloudLLMStatus

    credential_configured: bool
    api_key_hint: str

    max_images: int
    max_model_len: int
    is_chat_model: bool
    supports_reasoning: bool
    supports_reasoning_effort: bool
    supports_tool_calling: bool