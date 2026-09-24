# domain/enums.py

from enum import StrEnum


class CloudLLMProvider(StrEnum):
    GEMINI = "gemini"
    OPENAI_COMPATIBLE = "openai_compatible"


class CloudLLMStatus(StrEnum):
    UNTESTED = "untested"
    AVAILABLE = "available"
    AUTHENTICATION_FAILED = "authentication_failed"
    MODEL_NOT_FOUND = "model_not_found"
    RATE_LIMITED = "rate_limited"
    UNREACHABLE = "unreachable"
    DISABLED = "disabled"