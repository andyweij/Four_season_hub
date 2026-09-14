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
    DELTA = "delta"
    DONE = "done"
    ERROR = "error"