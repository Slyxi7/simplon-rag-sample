import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from rag.config.logging import request_id, conversation_id, get_logger

logger = get_logger("middleware")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request_id and timing to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        req_id = str(uuid.uuid4())
        request_id.set(req_id)
        
        # Extract conversation_id from headers if present
        conv_id = request.headers.get("X-Conversation-ID")
        if conv_id:
            conversation_id.set(conv_id)
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                "event": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent", ""),
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "event": "request_complete",
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = req_id
            
            return response
            
        except Exception as e:
            # Calculate latency for failed requests
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "event": "request_error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:200],  # Truncate to avoid logs
                    "latency_ms": latency_ms,
                },
                exc_info=True
            )
            raise