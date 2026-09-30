"""Health Check and Readiness Endpoints."""

from typing import Any
from fastapi import APIRouter, Depends
import onnxruntime as ort
from app.api.deps import get_engine_manager_dep
from app.engine.manager import EngineManager

router = APIRouter()


@router.get("/health", summary="Health and readiness check")
async def health_check(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> dict[str, Any]:
    """Check service health, model readiness, and available ONNX execution providers."""
    return {
        "status": "ok",
        "models_ready": manager.is_ready,
        "available_providers": ort.get_available_providers(),
    }
