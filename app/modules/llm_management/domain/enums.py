from enum import StrEnum


class ModelRuntimeStatus(StrEnum):
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    STARTING = "starting"
    READY = "ready"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"