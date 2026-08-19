import logging
from logging.config import dictConfig
from pathlib import Path
from app.core.context import session_id_context

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"


class SessionContextFilter(logging.Filter):
    def filter(
            self,
            record: logging.LogRecord,
    ) -> bool:
        record.sid = session_id_context.get()

        return True


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,

            "filters": {
                "session_context": {
                    "()": SessionContextFilter,
                },
            },

            "formatters": {
                "standard": {
                    "format": (
                        "%(asctime)s "
                        "[%(levelname)s] "
                        "[SID=%(sid)s] "
                        "%(name)s - "
                        "%(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },

            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": [
                        "session_context",
                    ],
                    "level": "INFO",
                },

                "daily_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "formatter": "standard",
                    "filters": [
                        "session_context",
                    ],
                    "level": "INFO",

                    "filename": str(LOG_DIR / "app.log"),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 30,

                    "encoding": "utf-8",
                    "delay": True,
                    "utc": False,
                },
            },

            "loggers": {
                "app.http": {
                    "handlers": [
                        "console",
                        "daily_file",
                    ],
                    "level": "INFO",
                    "propagate": False,
                },
                "app": {
                    "handlers": [
                        "console",
                        "daily_file",
                    ],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )
