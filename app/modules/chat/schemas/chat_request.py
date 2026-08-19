from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.fields import Field
from app.modules.chat.schemas.generation_parameters import GenerationParameters


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, max_length=200)
    message: list[ChatMessage] = Field(min_length=1)
    stream: bool = False

    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
