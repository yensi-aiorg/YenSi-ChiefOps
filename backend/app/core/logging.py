from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

import orjson


class JSONFormatter(logging.Formatter):
    """Produce structured JSON log lines suitable for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.name == "uvicorn.access":
            log_entry["logger"] = "access"

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id  # type: ignore[attr-defined]

        extra_keys = {
            k
            for k in record.__dict__
            if k
            not in {
                "name",
                "msg",
                "args",
                "created",
                "relativeCreated",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "pathname",
                "filename",
                "module",
                "levelno",
                "levelname",
                "msecs",
                "thread",
                "threadName",
                "process",
                "processName",
                "message",
                "taskName",
                "request_id",
            }
        }
        for key in extra_keys:
            value = record.__dict__[key]
            if isinstance(value, str | int | float | bool | type(None)):
                log_entry[key] = value

        return orjson.dumps(log_entry).decode("utf-8")


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with structured JSON output.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers to avoid duplicate output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(stream_handler)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(max(numeric_level, logging.INFO))
    logging.getLogger("uvicorn.error").setLevel(max(numeric_level, logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("motor").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("pymongo").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("redis").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("httpx").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("httpcore").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("watchfiles").setLevel(max(numeric_level, logging.WARNING))
