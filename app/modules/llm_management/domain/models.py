from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelCatalogEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    model_key: str

    model_type: str = Field(
        alias="modelType",
    )

    relative_path: str = Field(
        alias="relativePath",
    )
    entry_point: str | None = Field(
        default=None,
        alias="entryPoint",
    )

    engine_type: str = Field(
        alias="engineType",
    )

    engine_image_name: str | None = Field(
        default=None,
        alias="engineImageName",
    )

    size: int = Field(
        ge=0,
        strict=True,
    )

    max_images: int = Field(
        alias="imagesSupport",
        ge=0,
        strict=True,
    )

    supports_reasoning: bool = Field(
        alias="reasoning",
        strict=True,
    )

    supports_reasoning_effort: bool = Field(
        default=False,
        alias="reasoningEffort",
        strict=True,
    )

    is_chat_model: bool = Field(
        alias="isChatModel",
        strict=True,
    )

    model_config_data: dict[str, Any] = Field(
        alias="modelConfig",
    )

    launch_config: dict[str, Any] = Field(
        alias="launchConfig",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
