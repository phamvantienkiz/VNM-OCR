"""Document Layout Analysis Endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from app.api.deps import get_layout_service
from app.services.layout_service import LayoutService
from app.schemas.layout import LayoutResponse

router = APIRouter()


@router.post(
    "/layout",
    response_model=LayoutResponse,
    summary="Analyze document layout regions",
    description="Detects layout elements (Title, Text, Table, Figure, Caption, Equation) using YOLOv10 ONNX.",
)
async def analyze_layout(
    file: UploadFile = File(..., description="Document page image file"),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0, description="Confidence threshold"),
    service: LayoutService = Depends(get_layout_service),
) -> LayoutResponse:
    """Run Document Layout Analysis on an uploaded page image."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    return service.process_image(content, threshold=threshold)
