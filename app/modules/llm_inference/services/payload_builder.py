from typing import Callable
from app.modules.llm_inference.domain.inference_request import InferenceRequest

PayloadBuilder = Callable[[dict, InferenceRequest], dict]


def build_common_payload(inference_request: InferenceRequest, stream: bool = True) -> dict:
    payload = {
        "model": inference_request.model,
        "messages": [message.model_dump() for message in inference_request.messages],
        "temperature": inference_request.temperature,
        "top_p": inference_request.top_p,
        "max_tokens": inference_request.max_tokens,
        "stream": stream,
    }
    if stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


def _add_reasoning_effort(payload: dict, inference_request: InferenceRequest) -> dict:
    if inference_request.reasoning_effort:
        payload["reasoning_effort"] = inference_request.reasoning_effort
    return payload


_MODEL_TYPE_BUILDERS: dict[str, PayloadBuilder] = {
    "gpt-oss": _add_reasoning_effort,
}


def build_chat_payload(inference_request: InferenceRequest, stream: bool = True
                       ) -> dict:
    payload = build_common_payload(inference_request, stream=stream)
    model_type = inference_request.model_type

    extra_builder = _MODEL_TYPE_BUILDERS.get(model_type)
    if extra_builder is not None:
        payload = extra_builder(payload, inference_request)
    return payload
