"""OCR Endpoints."""

import asyncio
from typing import Any
from fastapi import APIRouter, Depends, File, UploadFile, Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.api.deps import get_ocr_service
from app.services.ocr_service import OcrService
from app.schemas.ocr import OCRResponse

router = APIRouter()
legacy_router = APIRouter()


@router.post(
    "/ocr",
    response_model=OCRResponse,
    summary="Perform OCR on a single image",
    description="Accepts an image file (PNG, JPG, WEBP, etc.) and returns detected text lines with bounding boxes and confidence scores.",
)
async def recognize_image(
    request: Request,
    file: UploadFile = File(..., description="Image file to process"),
    service: OcrService = Depends(get_ocr_service),
) -> Any:
    """Run OCR detection and recognition on an uploaded image file."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    ocr_sem: asyncio.Semaphore = getattr(request.app.state, "ocr_semaphore", None) or asyncio.Semaphore(1)
    ocr_acquired = False
    try:
        try:
            async with asyncio.timeout(10.0):
                await ocr_sem.acquire()
                ocr_acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Hệ thống OCR đang bận. Thử lại sau."},
                headers={"Retry-After": "30"},
            )

        try:
            async with asyncio.timeout(120.0):
                await file.seek(0)
                return await asyncio.to_thread(service.process_image_file, file.file)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý OCR (Processing Timeout)."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()
        await file.close()


@legacy_router.post(
    "/api/ocr",
    tags=["Legacy UI Adapter"],
    summary="Legacy OCR endpoint for UI compatibility",
    description="Returns nested list format [[[x1, y1], ...], [text, score]] matching existing demo UI.",
)
async def legacy_ocr_endpoint(
    request: Request,
    file: UploadFile = File(..., description="Image file to process"),
    service: OcrService = Depends(get_ocr_service),
) -> Any:
    """Legacy OCR endpoint matching original server.py response format."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    ocr_sem: asyncio.Semaphore = getattr(request.app.state, "ocr_semaphore", None) or asyncio.Semaphore(1)
    ocr_acquired = False
    try:
        try:
            async with asyncio.timeout(10.0):
                await ocr_sem.acquire()
                ocr_acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Hệ thống OCR đang bận. Thử lại sau."},
                headers={"Retry-After": "30"},
            )

        try:
            async with asyncio.timeout(120.0):
                await file.seek(0)
                return await asyncio.to_thread(service.process_image_legacy, file.file)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý OCR (Processing Timeout)."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()
        await file.close()
