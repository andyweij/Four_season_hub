from typing import Callable
from app.modules.chat.schemas.chat_request import ChatMessage, GenerationParameters

PayloadBuilder = Callable[[dict, dict], dict]


def build_common_payload(model: str, messages: list[ChatMessage], parameters: GenerationParameters) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": parameters.temperature,
        "top_p": parameters.top_p,
        "max_tokens": parameters.max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    return payload


def _add_reasoning_effort(payload: dict, parameters: dict) -> dict:
    if parameters.get("reasoning_effort"):
        payload["reasoning_effort"] = parameters["reasoning_effort"]
    return payload


_MODEL_TYPE_BUILDERS: dict[str, PayloadBuilder] = {
    "gpt-oss": _add_reasoning_effort,
}


def build_chat_payload(model_type: str, model: str, messages: list[ChatMessage],
                       parameters: GenerationParameters) -> dict:
    payload = build_common_payload(model, messages, parameters)
    extra_builder = _MODEL_TYPE_BUILDERS.get(model_type)
    if extra_builder is not None:
        payload = extra_builder(payload, parameters)
    return payload
