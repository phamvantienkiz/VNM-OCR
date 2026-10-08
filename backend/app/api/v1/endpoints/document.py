"""Document Extraction Endpoints for RAG & Chatbot Pipelines."""

import asyncio
from typing import Any
from fastapi import APIRouter, Depends, File, UploadFile, Query, Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.api.deps import get_document_service, get_dispatcher_service
from app.services.document_service import DocumentService
from app.services.dispatcher import UniversalDocumentDispatcher
from app.schemas.document import DocumentExtractionResponse

router = APIRouter()


@router.post(
    "/document/extract",
    response_model=DocumentExtractionResponse,
    summary="Extract full structured Markdown from PDF or image document",
    description=(
        "Unified pipeline for RAG Ingestion: renders PDF pages, performs layout analysis, "
        "recognizes Vietnamese OCR, converts tables into Markdown, and merges all content "
        "into a single structured Markdown text with natural reading order."
    ),
)
async def extract_document(
    request: Request,
    file: UploadFile = File(..., description="PDF document or image file to extract"),
    extract_tables: bool = Query(default=True, description="Whether to extract and format tables to Markdown"),
    resolution: int = Query(default=150, ge=72, le=300, description="Rendering resolution DPI for PDF pages"),
    service: DocumentService = Depends(get_document_service),
) -> Any:
    """Extract structured Markdown and per-page layout breakdown from a PDF or image file."""
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
                content={"detail": "Hệ thống OCR đang bận phục vụ tác vụ khác. Vui lòng thử lại sau."},
                headers={"Retry-After": "30"},
            )

        try:
            async with asyncio.timeout(120.0):
                await file.seek(0)
                return await asyncio.to_thread(
                    service.extract_document,
                    file_input=file.file,
                    extract_tables=extract_tables,
                    resolution=resolution,
                )
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý OCR (Processing Timeout) do tài liệu quá phức tạp."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()
        await file.close()


@router.post(
    "/document/smart-extract",
    response_model=DocumentExtractionResponse,
    summary="Smart Document Extraction with Automatic Fast-Path Fallback",
    description=(
        "Analyzes document with SmartPDFInspector. If digital, extracts directly with high speed (<50ms/page). "
        "If scanned or complex, routes through the full neural ONNX pipeline."
    ),
)
@router.post(
    "/extract/smart-document",
    response_model=DocumentExtractionResponse,
    summary="Alias for Smart Document Extraction",
    include_in_schema=True,
)
async def smart_extract_document(
    request: Request,
    file: UploadFile = File(..., description="PDF or image file to smartly extract"),
    extract_tables: bool = Query(default=True, description="Whether to extract and format tables to Markdown"),
    resolution: int = Query(default=150, ge=72, le=300, description="Rendering resolution DPI for PDF pages"),
    dispatcher: UniversalDocumentDispatcher = Depends(get_dispatcher_service),
) -> Any:
    """Classifies document and smartly routes through Fast Path or Heavy Neural Pipeline."""
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
                content={"detail": "Hệ thống OCR đang bận. Vui lòng thử lại sau."},
                headers={"Retry-After": "30"},
            )

        try:
            async with asyncio.timeout(120.0):
                await file.seek(0)
                return await asyncio.to_thread(
                    dispatcher.dispatch,
                    file_input=file.file,
                    extract_tables=extract_tables,
                    resolution=resolution,
                    filename=file.filename,
                )
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý tài liệu."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()
        await file.close()
