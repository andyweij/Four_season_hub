from app.infrastructure.config.settings import (
    CacheBackend,
    ModelCatalogBackend,
    RuntimeType,
    Settings,
)
from app.modules.llm_management.cache.memory import (
    MemoryRuntimeStatusCache,
)
# from app.modules.llm_management.cache.redis import (
#     RedisRuntimeStatusCache,
# )
from app.modules.llm_management.runtimes.docker import (
    DockerRuntimeInspector,
)
# from app.modules.llm_management.runtimes.native import (
#     NativeRuntimeInspector,
# )
from app.modules.llm_management.runtimes.podman import (
    PodmanRuntimeInspector,
)
from pathlib import Path

from app.modules.llm_management.catalog_loader import (
    load_catalog_file,
)
from app.modules.llm_management.repositories.memory_model_catalog import (
    InMemoryModelCatalog,
)

from app.modules.llm_management.artifacts.local import (
    LocalArtifactInspector,
)


def build_runtime_cache(
        settings: Settings,
        redis_client=None,
):
    match settings.cache_backend:
        case CacheBackend.MEMORY:
            return MemoryRuntimeStatusCache()

        case CacheBackend.REDIS:
            if redis_client is None:
                raise RuntimeError(
                    "Redis client is required "
                    "when cache backend is redis"
                )

            # return RedisRuntimeStatusCache(
            #     redis_client=redis_client
            # )

        case _:
            raise ValueError(
                f"Unsupported cache backend: "
                f"{settings.cache_backend}"
            )


def build_runtime_inspector(
        settings: Settings,
):
    match settings.runtime_type:
        case RuntimeType.DOCKER:
            return DockerRuntimeInspector()

        case RuntimeType.PODMAN:
            return PodmanRuntimeInspector()

        # case RuntimeType.NATIVE:
        #     return NativeRuntimeInspector()

        case _:
            raise ValueError(
                f"Unsupported runtime type: "
                f"{settings.runtime_type}"
            )


def build_memory_model_catalog(
        catalog_path: Path,
) -> InMemoryModelCatalog:
    entries = load_catalog_file(catalog_path)

    return InMemoryModelCatalog(
        entries=entries
    )


def build_model_catalog(
        settings: Settings,
        # database_session_factory=None,
):
    match settings.model_catalog_backend:
        case ModelCatalogBackend.MEMORY:
            return build_memory_model_catalog(
                catalog_path=settings.model_catalog_path
            )

        # case ModelCatalogBackend.POSTGRES:
        #     if database_session_factory is None:
        #         raise RuntimeError(
        #             "Database session factory is required"
        #         )
        #
        #     return PostgresModelCatalogRepository(
        #         session_factory=database_session_factory
        #     )

        case _:
            raise ValueError(
                f"Unsupported catalog backend: "
                f"{settings.model_catalog_backend}"
            )


def build_artifact_inspector(
        settings: Settings,
) -> LocalArtifactInspector:
    return LocalArtifactInspector(
        model_base_path=settings.model_base_path
    )
