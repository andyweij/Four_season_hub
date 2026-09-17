from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationList(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., alias="conversationId")
    user_id: str
    title: str | None = None
    model: str = Field(..., alias="selectModel")
    message_seq: int = 0
    created_at: datetime
    updated_at: datetime = Field(..., alias="lastModifyDttm")
