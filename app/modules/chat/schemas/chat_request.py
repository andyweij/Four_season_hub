from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.fields import Field
from app.modules.chat.schemas.generation_parameters import GenerationParameters
from app.modules.chat.domain.enums import ChatContentType


class ImageUrl(BaseModel):
    url: str


class ChatContent(BaseModel):
    type: ChatContentType = ChatContentType.TEXT
    text: str
    image_url: ImageUrl | None = None


class ChatMessage(BaseModel):
    role: str
    content: list[ChatContent]

    def extract_text(self) -> str:
        return "".join(
            part.text for part in self.content if part.type == ChatContentType.TEXT
        )

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    thinking: bool = False
    reasoning_effort: bool = False

    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
