"""Middleware for HTTP metrics collection."""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from rag.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    health_request_duration_seconds
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP RED metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Determine endpoint category
        endpoint = self._categorize_endpoint(request.url.path)
        method = request.method
        
        response = await call_next(request)
        
        # Record metrics
        status_code = str(response.status_code)
        duration = time.time() - start_time
        
        # Use specific histogram for health endpoint
        if endpoint == "health":
            health_request_duration_seconds.observe(duration)
        else:
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        return response
    
    def _categorize_endpoint(self, path: str) -> str:
        """Categorize endpoint for metrics."""
        if "/health" in path:
            return "health"
        elif "/chat" in path:
            return "messages"
        elif "/documents/ingest" in path:
            return "documents_ingest"
        elif "/eval/run" in path:
            return "eval_run"
        elif "/documents" in path:
            return "documents"
        elif "/eval" in path:
            return "eval"
        else:
            return "other"