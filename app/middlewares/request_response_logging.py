import logging
from time import perf_counter
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from uuid import uuid4

from app.core.context import session_id_context

logger = logging.getLogger("app.http")

MAX_LOG_BODY_BYTES = 4096


def body_preview(body: bytearray, total_size: int) -> str:
    text = bytes(body).decode("utf-8", errors="replace")

    if total_size > len(body):
        return f"{text}... <truncated>"

    return text


class RequestResponseLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send,
    ) -> None:
        # WebSocket 等非 HTTP 請求直接放行
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        sid = str(uuid4())
        sid_token = session_id_context.set(sid)

        request_body = bytearray()
        response_body = bytearray()

        request_total = 0
        response_total = 0
        status_code = 500

        async def receive_wrapper() -> Message:
            nonlocal request_total

            message = await receive()

            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                request_total += len(chunk)

                remaining = MAX_LOG_BODY_BYTES - len(request_body)

                if remaining > 0:
                    request_body.extend(chunk[:remaining])

            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_total, status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                response_total += len(chunk)

                remaining = MAX_LOG_BODY_BYTES - len(response_body)

                if remaining > 0:
                    response_body.extend(chunk[:remaining])

            # 重要：原始 response 仍要傳給客戶端
            await send(message)

        method = scope.get("method", "")
        path = scope.get("path", "")
        started_at = perf_counter()
        try:
            try:
                await self.app(
                    scope,
                    receive_wrapper,
                    send_wrapper,
                )

            except Exception:
                logger.exception(
                    "HTTP request failed: method=%s path=%s",
                    method,
                    path,
                )
                raise

            finally:
                elapsed_ms = (perf_counter() - started_at) * 1000

                logger.info(
                    (
                        "HTTP method=%s path=%s status=%s "
                        "duration_ms=%.2f request_body=%r response_body=%r"
                    ),
                    method,
                    path,
                    status_code,
                    elapsed_ms,
                    body_preview(request_body, request_total),
                    body_preview(response_body, response_total),
                )
        finally:
            session_id_context.reset(sid_token)
