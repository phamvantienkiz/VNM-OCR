"""OCR Endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from app.api.deps import get_ocr_service
from app.services.ocr_service import OcrService
from app.schemas.ocr import OCRResponse

router = APIRouter()


@router.post(
    "/ocr",
    response_model=OCRResponse,
    summary="Perform OCR on a single image",
    description="Accepts an image file (PNG, JPG, WEBP, etc.) and returns detected text lines with bounding boxes and confidence scores.",
)
async def recognize_image(
    file: UploadFile = File(..., description="Image file to process"),
    service: OcrService = Depends(get_ocr_service),
) -> OCRResponse:
    """Run OCR detection and recognition on an uploaded image file."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    return service.process_image(content)
