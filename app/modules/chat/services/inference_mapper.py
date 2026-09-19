from app.modules.llm_inference.domain.inference_request import InferenceRequest, InferenceMessage, InferenceContent
from app.modules.chat.schemas.chat_request import ChatMessage
from app.modules.llm_inference.domain.enums import InferenceRole, InferenceContentType
from app.modules.llm_inference.domain.inference_request import ImageUrl


def to_inference_message(message: ChatMessage) -> InferenceMessage:
    return InferenceMessage(
        role=InferenceRole(message.role),
        content=[
            InferenceContent(type=InferenceContentType(part.type.value), text=part.text,
                             image_url=ImageUrl(url=part.image_url.url) if part.image_url else None)
            for part in message.content
        ],
    )
