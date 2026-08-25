"""Structured Logging configuration for the application."""

import logging
import logging.config
from pathlib import Path
from app.core.config import settings

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"


def setup_logging() -> None:
    """Initialize logging configuration with console and rotating file handlers."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "app.log"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "console": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": settings.LOG_LEVEL,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_file),
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "formatter": "default",
                "level": settings.LOG_LEVEL,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console", "file"],
        },
    }

    logging.config.dictConfig(logging_config)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
