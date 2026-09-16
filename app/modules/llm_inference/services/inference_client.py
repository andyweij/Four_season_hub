# app/modules/llm_inference/services/inference_client.py
import json
from collections.abc import AsyncIterator

import httpx

from app.modules.llm_inference.domain.chat_delta import ChatDelta
from app.modules.llm_inference.exceptions import UpstreamInferenceError
from app.modules.llm_inference.services.payload_builder import build_chat_payload
from app.modules.llm_inference.services.think_tag_parser import ThinkTagParser
from app.modules.llm_inference.domain.inference_request import InferenceRequest


class InferenceClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def stream_chat_completion(
            self,
            endpoint: str,
            inference_request: InferenceRequest,
    ) -> AsyncIterator[ChatDelta]:
        payload = build_chat_payload(inference_request)
        think_parser = ThinkTagParser()
        async with self._http_client.stream(
                "POST", f"{endpoint}/v1/chat/completions", json=payload, timeout=None,
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise UpstreamInferenceError(response.status_code, body.decode(errors="replace"))

            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    return
                yield self._parse_chunk(json.loads(data), think_parser)

    @staticmethod
    def _parse_chunk(chunk: dict, think_parser: ThinkTagParser) -> ChatDelta:
        choices = chunk.get("choices") or []
        if not choices:
            return ChatDelta(content="", usage=chunk.get("usage"))

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")
        reasoning_content = delta.get("reasoning_content") or None
        content = delta.get("content") or ""

        if reasoning_content is None:
            segments = think_parser.feed(content)
            if finish_reason:
                segments += think_parser.flush()
            content = "".join(text for is_thinking, text in segments if not is_thinking)
            reasoning_content = "".join(text for is_thinking, text in segments if is_thinking) or None

        return ChatDelta(
            content=content,
            reasoning_content=reasoning_content,
            finish_reason=finish_reason,
            usage=chunk.get("usage"),
        )