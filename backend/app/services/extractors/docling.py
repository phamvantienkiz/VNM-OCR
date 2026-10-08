"""DoclingUniversalExtractor — Office & HTML document extraction.
Optional dependency: docling. Nếu chưa cài → HTTP 501.
"""

import logging
import time
import os
import tempfile
from typing import Any, BinaryIO

from app.exceptions.custom import ExtractorNotAvailableError
from app.schemas.document import (
    DocumentExtractionResponse,
    DocumentPageResult,
    ExtractionMetadata,
)
from app.schemas.ocr import OCRLineResult
from app.services.extractors.base import BaseExtractor
from app.utils.memory_utils import force_garbage_collection_and_trim

logger = logging.getLogger(__name__)


def _check_docling_available() -> bool:
    try:
        import importlib
        importlib.import_module("docling")
        return True
    except ImportError:
        return False


class DoclingUniversalExtractor(BaseExtractor):
    """Extracts content from Office documents and HTML using Docling.

    Supported: .docx, .xlsx, .pptx, .html, .htm
    OCR sub-engines are disabled to minimize RAM.
    """

    @property
    def name(self) -> str:
        return "docling_universal"

    @property
    def requires_image_input(self) -> bool:
        return False

    @property
    def supported_extensions(self) -> set[str]:
        return {".docx", ".xlsx", ".pptx", ".html", ".htm"}

    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        if not _check_docling_available():
            raise ExtractorNotAvailableError(
                extractor_name="DoclingUniversalExtractor",
                install_hint="pip install .[extractors]",
            )

        start_time = time.perf_counter()
        try:
            from docling.document_converter import DocumentConverter

            if hasattr(file_input, "read"):
                file_input.seek(0)
                file_bytes = file_input.read()
                file_input.seek(0)
            else:
                file_bytes = file_input

            filename = kwargs.get("filename", "document.docx")
            suffix = os.path.splitext(filename)[1] or ".docx"

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                converter = DocumentConverter()
                result = converter.convert(tmp_path)
                full_md = result.document.export_to_markdown()

                lines = [line.strip() for line in full_md.splitlines() if line.strip()]
                text_lines = [
                    OCRLineResult(bbox=[[0, 0], [0, 0], [0, 0], [0, 0]], text=line, score=1.0)
                    for line in lines
                ]

                page_res = DocumentPageResult(
                    page_number=1,
                    text_lines=text_lines,
                    layout_regions=[],
                    tables_markdown=[],
                    page_markdown=full_md,
                )

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                return DocumentExtractionResponse(
                    total_pages=1,
                    full_markdown=full_md,
                    pages=[page_res],
                    elapsed_ms=round(elapsed_ms, 2),
                    metadata=ExtractionMetadata(
                        pipeline_used=self.name,
                        requires_image_input=self.requires_image_input,
                    ),
                )
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        finally:
            force_garbage_collection_and_trim()
