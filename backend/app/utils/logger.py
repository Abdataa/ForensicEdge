"""
backend/app/utils/logger.py
-----------------------------
Structured logging setup for the ForensicEdge backend.

Replaces bare print() statements in services with proper log records
that include timestamps, log levels, module names, and can be
redirected to files or external logging services.

Usage
-----
    from app.utils.logger import get_logger

    logger = get_logger(__name__)

    logger.info("Image uploaded", extra={"image_id": 42, "user_id": 7})
    logger.warning("Processing slow", extra={"elapsed_ms": 3200})
    logger.error("Embedding failed", extra={"image_id": 42}, exc_info=True)

Log levels
----------
    DEBUG   — detailed diagnostic info (only shown when DEBUG=True)
    INFO    — normal operations (uploads, comparisons, logins)
    WARNING — recoverable issues (slow processing, missing optional files)
    ERROR   — failures that need attention (processing failed, DB error)
    CRITICAL— system cannot continue (model not loaded, DB unreachable)

Log format (JSON-structured for production log aggregators)
------------------------------------------------------------
    {
        "timestamp": "2025-12-01T14:23:11Z",
        "level":     "INFO",
        "module":    "app.services.image_service",
        "message":   "Image uploaded",
        "image_id":  42,
        "user_id":   7
    }
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib  import Path
from typing   import Any

from app.core.config import settings


# ---------------------------------------------------------------------------
# JSON formatter for structured log output
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.
    Structured logs are easier to query in log aggregators (Grafana, ELK).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "module":    record.name,
            "message":   record.getMessage(),
        }

        # Include any extra fields passed via extra={...}
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "message",
                "taskName",
            ):
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Plain text formatter for development / readability
# ---------------------------------------------------------------------------

class DevFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    Shown when DEBUG=True.
    """
    COLOURS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour  = self.COLOURS.get(record.levelname, "")
        message = record.getMessage()
        ts      = datetime.now(timezone.utc).strftime("%H:%M:%S")
        base    = f"{colour}[{record.levelname}]{self.RESET} {ts} {record.name}: {message}"

        # Append extra fields inline
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in (
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "message",
                "taskName",
            )
        }
        if extras:
            base += f"  {extras}"

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.

    Args:
        name : typically __name__ — gives the module path as the logger name
               e.g. "app.services.image_service"

    Returns:
        A logging.Logger instance with handlers already configured.
        Multiple calls with the same name return the same logger (singleton).

    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": 5, "email": "..."})
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        DevFormatter() if settings.DEBUG else JSONFormatter()
    )
    logger.addHandler(console_handler)

    # File handler — writes JSON logs to storage/logs/app.log
    log_dir = Path(settings.LOGS_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # Don't propagate to root logger (prevents duplicate output)
    logger.propagate = False

    return logger


# ---------------------------------------------------------------------------
# Module-level app logger (used in main.py and other top-level files)
# ---------------------------------------------------------------------------
app_logger = get_logger("forensicedge")
