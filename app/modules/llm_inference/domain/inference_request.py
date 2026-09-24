from pydantic import BaseModel
from app.modules.llm_inference.domain.enums import InferenceContentType, InferenceRole


class ImageUrl(BaseModel):
    url: str


class InferenceContent(BaseModel):
    type: InferenceContentType = InferenceContentType.TEXT
    text: str
    image_url: ImageUrl | None = None


class InferenceMessage(BaseModel):
    role: InferenceRole
    content: list[InferenceContent]


class InferenceRequest(BaseModel):
    model_type: str
    model: str
    messages: list[InferenceMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    reasoning_effort: bool = False
