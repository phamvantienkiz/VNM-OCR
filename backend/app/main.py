"""FastAPI Application Entry Point."""

# 1. Quản lý File Tạm (Sandboxing) — Tránh làm rác ổ C: trên Windows hoặc /tmp trên Linux (Issue #53)
import os
import sys
import tempfile
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)
tempfile.tempdir = str(TEMP_DIR)

# 2. Khóa cứng ngân sách luồng tính toán CPU đa nền tảng ngay từ đầu tiến trình
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

if sys.platform == "darwin":
    os.environ["VECLIB_MAXIMUM_THREADS"] = "2"

import cv2
cv2.setNumThreads(2)

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.api.v1.endpoints.ocr import legacy_router
from app.engine.manager import get_engine_manager
from app.engine.model_loader import clear_session_cache
from app.exceptions.handlers import register_exception_handlers
from app.middlewares import register_middlewares

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup warmup and graceful shutdown."""
    setup_logging()
    logger.info("Starting up %s (env=%s)...", settings.APP_NAME, settings.ENVIRONMENT)

    # Khởi tạo Semaphore khống chế 1 tác vụ tính toán OCR tại một thời điểm
    app.state.ocr_semaphore = asyncio.Semaphore(1)

    # Initialize EngineManager and warmup models
    try:
        manager = get_engine_manager(models_dir=settings.resolved_models_dir)
        manager.initialize()
        manager.warmup()
        logger.info("All OCR and Document models are warmed up and ready.")
    except Exception as e:
        logger.error("Failed to initialize engine manager during startup: %s", e)
        raise

    yield

    logger.info("Shutting down application and clearing session cache...")
    clear_session_cache()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-ready FastAPI service for Vietnamese OCR, Document Layout Analysis, and Table Extraction for RAG/Chatbots.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Setup Middlewares (UploadGuard, Backpressure, Chunked Stream Guard)
register_middlewares(app)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Custom Exception Handlers
register_exception_handlers(app)

# Include v1 API Router and Legacy UI Adapter Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(legacy_router)

# Static UI Mount (if ui directory exists)
ui_path = Path(__file__).resolve().parents[2] / "ui"
if ui_path.is_dir():
    app.mount("/ui", StaticFiles(directory=str(ui_path), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        """Redirect root to UI interface."""
        return RedirectResponse(url="/ui/index.html")
