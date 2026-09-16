from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    ERROR = "error"


class ChatEventType(StrEnum):
    ACK = "ack"
    THINKING_DELTA = "thinking_delta"
    DELTA = "delta"
    DONE = "done"
    ERROR = "error"

class ChatContentType(StrEnum):
    TEXT = "text"
    IMAGE = "image_url"


# class ChatModelRuntimeStatus(StrEnum):
#     NOT_INSTALLED = "not_installed"
#     INSTALLING = "installing"
#     INSTALLED = "installed"
#     STARTING = "starting"
#     READY = "ready"
#     UNHEALTHY = "unhealthy"
#     STOPPED = "stopped"
#     ERROR = "error"
#     UNKNOWN = "unknown"