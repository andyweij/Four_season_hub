from typing import Any

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    subject: str
    username: str | None = None
    email: str | None = None
    roles: set[str] = Field(default_factory=set)
    claims: dict[str, Any] = Field(default_factory=dict)