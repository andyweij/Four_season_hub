from contextvars import ContextVar


session_id_context: ContextVar[str] = ContextVar(
    "session_id",
    default="N/A",
)