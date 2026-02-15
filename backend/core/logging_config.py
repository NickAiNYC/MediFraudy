"""
Structured JSON logging for production.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
import os


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for log aggregation systems"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add custom fields from extra parameter
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "message", "pathname", "process", "processName",
                          "relativeCreated", "thread", "threadName", "exc_info",
                          "exc_text", "stack_info", "request_id", "user_id"]:
                log_data[key] = value
        
        return json.dumps(log_data)


def setup_logging():
    """
    Configure structured JSON logging for production.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    structured_logging = os.getenv("STRUCTURED_LOGGING", "true").lower() == "true"
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if structured_logging:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    logging.info(f"Logging configured: level={log_level}, structured={structured_logging}")


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs (PHI, passwords, tokens)"""
    
    SENSITIVE_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',  # Credit card
        r'Bearer [A-Za-z0-9\-._~+/]+=*',  # JWT tokens
        r'password["\s:=]+[^"\s]+',  # Passwords
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        import re
        
        message = record.getMessage()
        
        for pattern in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
        
        record.msg = message
        record.args = ()
        
        return True
