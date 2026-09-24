from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.postgres.base import Base


class CloudLLMRecord(Base):
    __tablename__ = "cloud_llm_connections"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    base_url: Mapped[str | None] = mapped_column(
        String(500),
    )

    encrypted_api_key: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    encryption_nonce: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    encryption_key_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    api_key_hint: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    max_images: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    max_model_len: Mapped[int] = mapped_column(
        Integer,
        default=-1,
        nullable=False,
    )

    is_chat_model: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    supports_reasoning: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    supports_reasoning_effort: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    supports_tool_calling: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    last_latency_ms: Mapped[int | None] = mapped_column(
        Integer,
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )