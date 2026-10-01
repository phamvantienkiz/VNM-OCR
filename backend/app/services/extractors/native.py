"""NativePDFExtractor — Ultra-fast vector text extraction for born-digital PDFs.

Extracts text directly from the PDF's internal text layer using pdfplumber,
completely bypassing image rendering, DLA, and OCR models.
Target latency: < 50ms per page. Peak RAM: < 200MB.
"""

import io
import logging
import time
from typing import Any, BinaryIO

import pdfplumber

from app.schemas.document import DocumentExtractionResponse, DocumentPageResult, ExtractionMetadata
from app.schemas.ocr import OCRLineResult
from app.services.extractors.base import BaseExtractor
from app.utils.memory_utils import force_garbage_collection_and_trim

logger = logging.getLogger(__name__)


class NativePDFExtractor(BaseExtractor):
    """Extracts text directly from born-digital PDFs without any neural inference.

    Ideal for:
      - PDFs generated from Word, LaTeX, or other digital authoring tools.
      - Documents classified as DIGITAL_DOCUMENT by SmartPDFInspector.

    Does NOT handle scanned PDFs, images, or corrupted-font PDFs.
    """

    @property
    def name(self) -> str:
        return "native_pdf"

    @property
    def requires_image_input(self) -> bool:
        return False

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        """Extract text vectors directly from PDF internal structures."""
        start_time = time.perf_counter()

        if hasattr(file_input, "read"):
            file_input.seek(0)
            file_obj = file_input
        else:
            file_obj = io.BytesIO(file_input)

        pages_result: list[DocumentPageResult] = []
        page_markdowns: list[str] = []

        try:
            with pdfplumber.open(file_obj) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF document contains no pages")

                for page_idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

                    # Build markdown from text lines
                    page_md = "\n".join(lines)

                    # Extract tables if requested
                    tables_markdown: list[str] = []
                    if extract_tables:
                        raw_tables = page.extract_tables() or []
                        for table in raw_tables:
                            if not table:
                                continue
                            md_table = _table_to_markdown(table)
                            if md_table.strip():
                                tables_markdown.append(md_table)
                                page_md += f"\n\n{md_table}"

                    text_lines_schema = [
                        OCRLineResult(
                            bbox=[[0, 0], [0, 0], [0, 0], [0, 0]],
                            text=line,
                            score=1.0,
                        )
                        for line in lines
                    ]

                    page_res = DocumentPageResult(
                        page_number=page_idx + 1,
                        text_lines=text_lines_schema,
                        layout_regions=[],
                        tables_markdown=tables_markdown,
                        page_markdown=page_md,
                    )
                    pages_result.append(page_res)
                    page_markdowns.append(page_md)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            full_markdown = "\n\n---\n\n".join([pm for pm in page_markdowns if pm.strip()])

            logger.info(
                "NativePDFExtractor completed: %d page(s), %.2f ms",
                len(pages_result),
                elapsed_ms,
            )

            return DocumentExtractionResponse(
                total_pages=len(pages_result),
                full_markdown=full_markdown,
                pages=pages_result,
                elapsed_ms=round(elapsed_ms, 2),
                metadata=ExtractionMetadata(
                    pipeline_used=self.name,
                    requires_image_input=self.requires_image_input,
                    is_vector_recovery=False,
                ),
            )
        finally:
            force_garbage_collection_and_trim()


def _table_to_markdown(table: list[list[str | None]]) -> str:
    """Convert a pdfplumber table (list of rows) to a Markdown table string."""
    if not table or not table[0]:
        return ""

    # Clean cells
    clean_table = []
    for row in table:
        clean_row = [(cell or "").strip().replace("\n", " ") for cell in row]
        clean_table.append(clean_row)

    # Build header
    header = clean_table[0]
    col_count = len(header)
    md_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * col_count) + " |",
    ]

    # Build data rows
    for row in clean_table[1:]:
        # Pad row if needed
        padded = row + [""] * (col_count - len(row))
        md_lines.append("| " + " | ".join(padded[:col_count]) + " |")

    return "\n".join(md_lines)
