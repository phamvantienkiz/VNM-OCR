"""Middlewares package."""

from fastapi import FastAPI
from app.middlewares.upload_guard import (
    StreamingUploadGuardMiddleware,
    MAX_UPLOAD_SIZE,
    MAX_CONCURRENT_UPLOADS,
)


def register_middlewares(app: FastAPI) -> None:
    """Register all cross-cutting middlewares in proper execution order."""
    app.add_middleware(
        StreamingUploadGuardMiddleware,
        max_upload_size=MAX_UPLOAD_SIZE,
        max_concurrent=MAX_CONCURRENT_UPLOADS,
    )
