"""Explicit Format Extraction Endpoints (Phase 6).

Endpoints:
  POST /extract/auto              — Smart auto-routing
  POST /extract/native/pdf        — Born-digital PDF only
  POST /extract/docling           — Office & HTML
  POST /extract/paddle/ocr        — English/International OCR
  POST /extract/paddle/complex-vlm — Paper/Math VLM
  POST /extract/vnm               — Vietnamese OCR (ONNX pipeline)
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, Query, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import (
    get_dispatcher,
    get_vnm_extractor,
    get_native_extractor,
    get_docling_extractor,
    get_paddle_extractor,
)
from app.services.dispatcher import UniversalDocumentDispatcher
from app.services.extractors.native import NativePDFExtractor
from app.services.extractors.vnm import VNMOCRExtractor
from app.services.extractors.docling import DoclingUniversalExtractor
from app.services.extractors.paddle import PaddleOCRExtractor
from app.schemas.document import DocumentExtractionResponse

router = APIRouter(prefix="/extract", tags=["Extract"])


async def _run_with_semaphore(
    request: Request,
    sync_fn: Any,
    *,
    timeout_acquire: float = 10.0,
    timeout_process: float = 120.0,
    **kwargs: Any,
) -> Any:
    """Acquire OCR semaphore → run sync function in thread → handle timeouts."""
    ocr_sem: asyncio.Semaphore = (
        getattr(request.app.state, "ocr_semaphore", None) or asyncio.Semaphore(1)
    )
    ocr_acquired = False
    try:
        try:
            async with asyncio.timeout(timeout_acquire):
                await ocr_sem.acquire()
                ocr_acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Hệ thống OCR đang bận. Vui lòng thử lại sau."},
                headers={"Retry-After": "30"},
            )

        try:
            async with asyncio.timeout(timeout_process):
                return await asyncio.to_thread(sync_fn, **kwargs)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý (Processing Timeout)."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()


def _validate_file(file: UploadFile) -> None:
    """Validate that a file was actually uploaded."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )


# ── 1. Auto-routing endpoint ────────────────────────────────────────

@router.post(
    "/auto",
    response_model=DocumentExtractionResponse,
    summary="Auto-classify & extract document",
    description=(
        "Automatically classifies the document type via SmartPDFInspector and routes "
        "to the optimal extraction pipeline. Returns pipeline_used in metadata."
    ),
)
async def extract_auto(
    request: Request,
    file: UploadFile = File(..., description="PDF or image file"),
    extract_tables: bool = Query(True, description="Extract tables to Markdown"),
    resolution: int = Query(150, ge=72, le=300, description="PDF rendering DPI"),
    dispatcher: UniversalDocumentDispatcher = Depends(get_dispatcher),
) -> Any:
    _validate_file(file)
    try:
        await file.seek(0)
        return await _run_with_semaphore(
            request,
            dispatcher.dispatch,
            file_input=file.file,
            extract_tables=extract_tables,
            resolution=resolution,
        )
    finally:
        await file.close()


# ── 2. Native PDF ───────────────────────────────────────────────────

@router.post(
    "/native/pdf",
    response_model=DocumentExtractionResponse,
    summary="Born-digital PDF fast extraction (< 50ms/page)",
)
async def extract_native_pdf(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    extractor: NativePDFExtractor = Depends(get_native_extractor),
) -> Any:
    _validate_file(file)
    try:
        await file.seek(0)
        return await _run_with_semaphore(
            request,
            extractor.extract,
            file_input=file.file,
            extract_tables=extract_tables,
            timeout_process=30.0,
        )
    finally:
        await file.close()


# ── 3. Docling (Office & HTML) ──────────────────────────────────────

@router.post(
    "/docling",
    response_model=DocumentExtractionResponse,
    summary="Office & HTML extraction via Docling",
)
async def extract_docling(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    extractor: DoclingUniversalExtractor = Depends(get_docling_extractor),
) -> Any:
    _validate_file(file)
    try:
        await file.seek(0)
        return await _run_with_semaphore(
            request,
            extractor.extract,
            file_input=file.file,
            extract_tables=extract_tables,
            filename=file.filename,
            timeout_process=60.0,
        )
    finally:
        await file.close()


# ── 4. PaddleOCR (English/International) ────────────────────────────

@router.post(
    "/paddle/ocr",
    response_model=DocumentExtractionResponse,
    summary="English/International OCR via PaddleOCR",
)
async def extract_paddle_ocr(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    resolution: int = Query(150, ge=72, le=300),
    extractor: PaddleOCRExtractor = Depends(get_paddle_extractor),
) -> Any:
    _validate_file(file)
    try:
        await file.seek(0)
        return await _run_with_semaphore(
            request,
            extractor.extract,
            file_input=file.file,
            extract_tables=extract_tables,
            resolution=resolution,
            mode="ocr",
        )
    finally:
        await file.close()


# ── 5. PaddleOCR Complex VLM (Paper/Math) ───────────────────────────

@router.post(
    "/paddle/complex-vlm",
    response_model=DocumentExtractionResponse,
    summary="Paper/Math extraction via PaddleOCR-VL",
)
async def extract_paddle_vlm(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    resolution: int = Query(150, ge=72, le=300),
    extractor: PaddleOCRExtractor = Depends(get_paddle_extractor),
) -> Any:
    _validate_file(file)
    try:
        await file.seek(0)
        return await _run_with_semaphore(
            request,
            extractor.extract,
            file_input=file.file,
            extract_tables=extract_tables,
            resolution=resolution,
            mode="complex-vlm",
            timeout_process=180.0,
        )
    finally:
        await file.close()


# ── 6. Vietnamese OCR ───────────────────────────────────────────────

@router.post(
    "/vnm",
    response_model=DocumentExtractionResponse,
    summary="Vietnamese OCR (ONNX pipeline: DBNet + YOLO + VietOCR)",
)
async def extract_vnm(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    resolution: int = Query(150, ge=72, le=300),
    extractor: VNMOCRExtractor = Depends(get_vnm_extractor),
) -> Any:
    _validate_file(file)
    try:
        await file.seek(0)
        return await _run_with_semaphore(
            request,
            extractor.extract,
            file_input=file.file,
            extract_tables=extract_tables,
            resolution=resolution,
        )
    finally:
        await file.close()
