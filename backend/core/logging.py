"""Structured JSON logging configuration for production use."""

import json
import logging
import sys
import os
from datetime import datetime
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Output log records as JSON for structured log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include extra fields if present
        for key in ("user", "provider_id", "action", "request_id"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry)


def setup_logging(level: Optional[str] = None, json_output: bool = True) -> None:
    """Configure application logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, format logs as JSON. Otherwise plain text.
    """
    log_level = getattr(logging, (level or os.getenv("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if json_output and os.getenv("ENVIRONMENT", "development") != "development":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root.addHandler(handler)
