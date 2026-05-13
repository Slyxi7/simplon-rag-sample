import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from pythonjsonlogger import jsonlogger


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for frontend logging."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add node identifier
        log_record['node'] = 'frontend'
        
        # Extract event from message if present
        if 'event' not in log_record:
            log_record['event'] = getattr(record, 'event', 'generic')


def setup_frontend_logging() -> None:
    """Configure structured logging for the frontend."""
    
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


def get_logger(name: str) -> logging.Logger:
    """Get a structured logger for frontend components."""
    return logging.getLogger(f"frontend.{name}")