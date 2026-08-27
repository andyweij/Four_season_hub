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
    DockerCompatRuntimeInspector,
)
from app.modules.llm_management.runtimes.windows_native import (
    WindowsNativeRuntimeInspector,
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

import platform
import os
import docker


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


def resolve_base_url(runtime_type: RuntimeType) -> str:
    system = platform.system()

    if system == "Windows":
        # Docker Desktop 與 Podman machine 在 Windows 上
        # 都轉發到同一個 named pipe（已實測驗證過）
        return "npipe:////./pipe/docker_engine"

    if system == "Darwin":
        # Docker Desktop / Podman machine for Mac 也各自走 unix socket
        # 路徑依安裝方式可能不同，通常在 ~/.docker/run/docker.sock
        # 或 ~/.local/share/containers/podman/machine/podman.sock
        ...

    # Linux（不需要透過虛擬機，直接連本機 socket）
    match runtime_type:
        case RuntimeType.DOCKER:
            return "unix:///var/run/docker.sock"
        case RuntimeType.PODMAN:
            uid = os.getuid()
            return f"unix:///run/user/{uid}/podman/podman.sock"
        case _:
            raise ValueError(f"Unsupported runtime type: {runtime_type}")


def build_docker_client(settings: Settings) -> docker.DockerClient | None:
    if settings.runtime_type not in (RuntimeType.DOCKER, RuntimeType.PODMAN):
        return None

    base_url = resolve_base_url(settings.runtime_type)
    return docker.DockerClient(base_url=base_url)


def build_runtime_inspector(
        settings: Settings,
        docker_client: docker.DockerClient | None,
):
    match settings.runtime_type:
        case RuntimeType.DOCKER | RuntimeType.PODMAN:
            if docker_client is None:
                raise RuntimeError(
                    "docker_client is required for docker/podman runtime"
                )
            return DockerCompatRuntimeInspector(docker_client)

        case RuntimeType.NATIVE:
            return WindowsNativeRuntimeInspector(
                model_base_path=settings.model_base_path,
            )

        case _:
            raise ValueError(f"Unsupported runtime type: {settings.runtime_type}")


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
