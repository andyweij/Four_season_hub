from pydantic import BaseModel, SecretStr


class UpdateCloudLLMRequest(BaseModel):
    name: str | None = None
    model_name: str | None = None
    base_url: str | None = None
    api_key: SecretStr | None = None
    enabled: bool | None = None