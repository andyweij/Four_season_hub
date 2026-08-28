from pydantic import BaseModel, ConfigDict, Field


class RunModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_name: str


class RunModelResponse(BaseModel):
    model_name: str
    status: str
    endpoint: str | None
