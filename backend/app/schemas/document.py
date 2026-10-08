"""Schemas for Document Extraction Pipeline (RAG/Chatbot Ingestion)."""

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.ocr import OCRLineResult
from app.schemas.layout import LayoutRegionResult


class DocumentPageResult(BaseModel):
    """Extraction results for an individual page."""

    page_number: int = Field(..., ge=1, description="Page index (1-based)")
    text_lines: list[OCRLineResult] = Field(default_factory=list, description="Extracted text lines")
    layout_regions: list[LayoutRegionResult] = Field(default_factory=list, description="Layout regions")
    tables_markdown: list[str] = Field(default_factory=list, description="Markdown strings of tables in page")
    page_markdown: str = Field(..., description="Complete structured Markdown for this page")

    model_config = ConfigDict(extra="forbid")


class ExtractionMetadata(BaseModel):
    """Routing and pipeline metadata attached to extraction responses."""

    pipeline_used: str = Field(..., description="Name of the extractor that processed the document")
    requires_image_input: bool = Field(
        default=False,
        description="Whether the engine required rendering pages to images (OCR pipelines)",
    )
    is_vector_recovery: bool = Field(
        default=False,
        description="Whether a digital PDF with broken fonts had to be rasterized and OCR'd",
    )
    classification: str | None = Field(
        default=None,
        description="SmartPDFInspector classification (DIGITAL_DOCUMENT, SCANNED_DOCUMENT, etc.)",
    )

    model_config = ConfigDict(extra="allow")


class DocumentExtractionResponse(BaseModel):
    """Full Document Extraction Response containing unified Markdown for RAG Pipelines."""

    total_pages: int = Field(..., ge=1, description="Total number of pages processed")
    full_markdown: str = Field(..., description="Unified structured Markdown text for RAG chunking")
    pages: list[DocumentPageResult] = Field(default_factory=list, description="Per-page breakdown")
    elapsed_ms: float = Field(..., description="Total execution duration in milliseconds")
    metadata: ExtractionMetadata | None = Field(
        default=None,
        description="Routing metadata: which pipeline was used, classification results, etc.",
    )

    model_config = ConfigDict(extra="forbid")
