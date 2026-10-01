from pydantic import BaseModel
from app.modules.agent_execution.schemas.execution_request import ModelRef
from pydantic import ConfigDict
from pydantic.fields import Field
from app.modules.chat.schemas.generation_parameters import GenerationParameters
from app.modules.chat.domain.enums import ChatContentType, MessageRole


class ImageUrl(BaseModel):
    url: str


class ChatContent(BaseModel):
    type: ChatContentType = ChatContentType.TEXT
    text: str
    image_url: ImageUrl | None = None


class ChatMessage(BaseModel):
    role: MessageRole = MessageRole.USER
    content: list[ChatContent]

    def extract_text(self) -> str:
        return "".join(
            part.text for part in self.content if part.type == ChatContentType.TEXT
        )


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(default="", alias="conversationId")
    model: str | None = Field(default=None, min_length=1, max_length=200)
    model_ref: ModelRef | None = Field(default=None, alias="modelRef")
    agent_id: str | None = Field(default=None, alias="agentId")
    agent_options: dict = Field(default_factory=dict, alias="agentOptions")
    messages: list[ChatMessage] = Field(min_length=1, max_length=1)
    stream: bool = False
    thinking: bool = False
    reasoning_effort: bool = False

    parameters: GenerationParameters = Field(default_factory=GenerationParameters)

    @property
    def parameters_supplied(self):
        return "parameters" in self.model_fields_set
