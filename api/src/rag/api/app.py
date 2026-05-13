from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag.api.middleware import RequestContextMiddleware
from rag.api.middleware_metrics import MetricsMiddleware
from rag.api.routers import chat, eval, health, ingestion, metrics
from rag.config.logging import setup_logging
from rag.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Simplon RAG Sample API",
        description="Sample RAG support chatbot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add metrics middleware first (to capture all requests)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(ingestion.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(eval.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")

    return app