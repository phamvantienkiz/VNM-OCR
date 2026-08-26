"""FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator
import logging
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.api.deps import get_ocr_service
from app.services.ocr_service import OcrService
from app.engine.manager import get_engine_manager
from app.engine.model_loader import clear_session_cache
from app.exceptions.handlers import register_exception_handlers

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup warmup and graceful shutdown."""
    setup_logging()
    logger.info("Starting up %s (env=%s)...", settings.APP_NAME, settings.ENVIRONMENT)

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

# Include v1 API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Legacy Adapter Endpoint for Existing Web UI Compatibility
@app.post(
    "/api/ocr",
    tags=["Legacy UI Adapter"],
    summary="Legacy OCR endpoint for UI compatibility",
    description="Returns nested list format [[[x1, y1], ...], [text, score]] matching existing demo UI.",
)
async def legacy_ocr_endpoint(
    file: UploadFile = File(...),
    service: OcrService = Depends(get_ocr_service),
) -> list[list[Any]]:
    """Legacy OCR endpoint matching original server.py response format."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    return service.process_image_legacy(content)


# Static UI Mount (if ui directory exists)
ui_path = Path(__file__).resolve().parents[2] / "ui"
if ui_path.is_dir():
    app.mount("/ui", StaticFiles(directory=str(ui_path), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        """Redirect root to UI interface."""
        return RedirectResponse(url="/ui/index.html")
