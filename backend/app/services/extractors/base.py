"""Base Extractor Interface (Strategy Pattern).

All document extractors must implement this interface to participate in the
UniversalDocumentDispatcher routing system.
"""

from abc import ABC, abstractmethod
from typing import Any, BinaryIO

from app.schemas.document import DocumentExtractionResponse


class BaseExtractor(ABC):
    """Base interface for all document extractors.

    Each concrete extractor declares:
      - name: identifier used in pipeline_used metadata.
      - requires_image_input: whether the engine needs pages rendered to images.
      - supported_extensions: file extensions this extractor can handle.
      - extract(): the core extraction logic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this extractor (used in metadata)."""
        ...

    @property
    def requires_image_input(self) -> bool:
        """Whether this extractor needs page images (OCR pipelines)."""
        return False

    @property
    def supported_extensions(self) -> set[str]:
        """File extensions this extractor accepts (e.g. {'.pdf', '.png'})."""
        return {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

    @abstractmethod
    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        """Extract document content and return standardized response.

        Args:
            file_input: File-like object or raw bytes.
            extract_tables: Whether to detect and convert tables to Markdown.
            resolution: Rendering DPI for PDF pages (ignored by non-PDF extractors).

        Returns:
            DocumentExtractionResponse with structured Markdown and page breakdown.
        """
        ...
