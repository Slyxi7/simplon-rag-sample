import logging
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

# Context variables for request tracing
request_id: ContextVar[str] = ContextVar('request_id', default='')
conversation_id: ContextVar[str] = ContextVar('conversation_id', default='')


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional structured fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add request context
        log_record['request_id'] = request_id.get()
        log_record['conversation_id'] = conversation_id.get()
        
        # Add node identifier
        log_record['node'] = 'api'
        
        # Extract event from message if present
        if 'event' not in log_record:
            log_record['event'] = getattr(record, 'event', 'generic')


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Create formatter
    formatter = StructuredFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a structured logger with the given name."""
    return logging.getLogger(f"rag.{name}")