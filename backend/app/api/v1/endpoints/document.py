"""Document Extraction Endpoints for RAG & Chatbot Pipelines."""

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from app.api.deps import get_document_service
from app.services.document_service import DocumentService
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
    file: UploadFile = File(..., description="PDF document or image file to extract"),
    extract_tables: bool = Query(default=True, description="Whether to extract and format tables to Markdown"),
    resolution: int = Query(default=150, ge=72, le=300, description="Rendering resolution DPI for PDF pages"),
    service: DocumentService = Depends(get_document_service),
) -> DocumentExtractionResponse:
    """Extract structured Markdown and per-page layout breakdown from a PDF or image file."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    return service.extract_document(
        file_bytes=content,
        extract_tables=extract_tables,
        resolution=resolution,
    )
