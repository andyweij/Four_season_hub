# domain/cloud_llm.py

from dataclasses import dataclass
from datetime import datetime

from .enums import CloudLLMProvider, CloudLLMStatus


@dataclass
class Capabilities:
    vision: bool
    streaming: bool
    reasoning: bool
    reasoning_effort: bool
    tool_calling: bool


@dataclass
class CloudLLM:
    id: str
    name: str
    provider: CloudLLMProvider
    model_name: str
    base_url: str | None

    enabled: bool
    status: CloudLLMStatus

    max_model_len: int
    capabilities: Capabilities

    api_key_hint: str
    credential_configured: bool

    last_tested_at: datetime | None
    last_latency_ms: int | None

    created_by: str
    created_at: datetime
    updated_at: datetime
