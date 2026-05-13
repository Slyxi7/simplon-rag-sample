"""Prometheus metrics for RAG application."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from functools import wraps
from typing import Callable, Any

# HTTP RED metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Fast health endpoint histogram
health_request_duration_seconds = Histogram(
    'health_request_duration_seconds',
    'Health endpoint duration in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

# RAG business metrics
guard_route_decisions = Counter(
    'guard_route_decisions_total',
    'Total guard route decisions',
    ['decision']  # in_scope, out_of_scope
)

escalations_total = Counter(
    'escalations_total',
    'Total escalations to human support'
)

evaluation_scores = Histogram(
    'evaluation_scores',
    'Evaluation scores distribution',
    buckets=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
)

evaluation_decisions = Counter(
    'evaluation_decisions_total',
    'Total evaluation decisions',
    ['decision']  # answer, rewrite, escalate
)

retrieved_chunks_count = Histogram(
    'retrieved_chunks_count',
    'Number of chunks retrieved per query',
    buckets=[0, 1, 2, 3, 5, 8, 12, 20, 30, 50]
)

# Node latency metrics
node_duration_seconds = Histogram(
    'node_duration_seconds',
    'Duration of RAG graph nodes',
    ['node_name'],  # guard_route, retrieve, generate, evaluate, etc.
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

def time_node(node_name: str):
    """Decorator to measure node execution time."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                node_duration_seconds.labels(node_name=node_name).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                node_duration_seconds.labels(node_name=node_name).observe(duration)
        
        return async_wrapper if hasattr(func, '__annotations__') and 'return' in func.__annotations__ else sync_wrapper
    return decorator