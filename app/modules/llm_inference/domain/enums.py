from enum import StrEnum


class InferenceRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InferenceContentType(StrEnum):
    TEXT = "text"
    IMAGE_URL = "image_url"