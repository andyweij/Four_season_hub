from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class RuntimeType(StrEnum):
    DOCKER = "docker"
    PODMAN = "podman"
    NATIVE = "native"


class ModelCatalogBackend(StrEnum):
    MEMORY = "memory"
    POSTGRES = "postgres"


class CacheBackend(StrEnum):
    MEMORY = "memory"
    REDIS = "redis"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    model_endpoint_host: str = "localhost"

    runtime_type: RuntimeType = RuntimeType.DOCKER

    model_catalog_backend: ModelCatalogBackend = (
        ModelCatalogBackend.MEMORY
    )

    model_catalog_path: Path = Path(
        "resources/models/models.json"
    )

    cache_backend: CacheBackend = CacheBackend.MEMORY

    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None

    runtime_check_interval_seconds: int = 10
    runtime_cache_ttl_seconds: int = 15
    model_base_path: Path
    model_artifact_check_on_startup: bool = True
    model_artifact_strict_startup: bool = False

    @model_validator(mode="after")
    def validate_backend_settings(self) -> "Settings":
        if (
                self.model_catalog_backend
                == ModelCatalogBackend.POSTGRES
                and self.database_url is None
        ):
            raise ValueError(
                "database_url is required "
                "when model_catalog_backend=postgres"
            )

        if (
                self.cache_backend == CacheBackend.REDIS
                and self.redis_url is None
        ):
            raise ValueError(
                "redis_url is required "
                "when cache_backend=redis"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
