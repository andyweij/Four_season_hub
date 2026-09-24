# domain/cloud_llm.py

from dataclasses import dataclass
from datetime import datetime

from .enums import CloudLLMProvider, CloudLLMStatus


@dataclass
class CloudLLM:
    id: str
    name: str
    provider: CloudLLMProvider
    model_name: str
    base_url: str | None

    enabled: bool
    status: CloudLLMStatus

    max_images: int
    max_model_len: int
    is_chat_model: bool
    supports_reasoning: bool
    supports_reasoning_effort: bool
    supports_tool_calling: bool

    api_key_hint: str
    credential_configured: bool

    last_tested_at: datetime | None
    last_latency_ms: int | None

    created_by: str
    created_at: datetime
    updated_at: datetime