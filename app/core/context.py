from contextvars import ContextVar


REQUEST_ID_HEADER = "X-Request-ID"


session_id_context: ContextVar[str] = ContextVar(
    "session_id",
    default="N/A",
)
