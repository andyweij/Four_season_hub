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
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    SOURCES = "sources"
    CANCELLED = "cancelled"
    ACK = "ack"
    THINKING_DELTA = "thinking_delta"
    DELTA = "delta"
    DONE = "done"
    ERROR = "error"

class ChatContentType(StrEnum):
    TEXT = "text"
    IMAGE = "image_url"
