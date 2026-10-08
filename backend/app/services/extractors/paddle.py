"""PaddleOCRExtractor — International OCR (English/multi-lang) and Complex VLM.
Optional dependency: paddleocr / paddlex.
"""

import io
import logging
import time
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
from app.utils.pdf_utils import load_document_images

logger = logging.getLogger(__name__)


def _check_paddle_available() -> bool:
    try:
        import importlib
        importlib.import_module("paddleocr")
        return True
    except ImportError:
        return False


class PaddleOCRExtractor(BaseExtractor):
    """PaddleOCR extractor for English/international documents.

    Two modes (selected via kwargs):
      - mode="ocr" (default): PP-OCRv4 for standard text extraction.
      - mode="complex-vlm": PaddleOCR-VL for papers, math, nested tables.
    """

    @property
    def name(self) -> str:
        return "paddle_ocr"

    @property
    def requires_image_input(self) -> bool:
        return True

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        if not _check_paddle_available():
            raise ExtractorNotAvailableError(
                extractor_name="PaddleOCRExtractor",
                install_hint="pip install .[extractors]  # includes paddleocr",
            )

        mode = kwargs.get("mode", "ocr")
        start_time = time.perf_counter()

        try:
            from paddleocr import PaddleOCR

            ocr_engine = PaddleOCR(use_angle_cls=True, lang="en")

            # Read file bytes
            if hasattr(file_input, "read"):
                file_input.seek(0)
                file_bytes = file_input.read()
                file_input.seek(0)
            else:
                file_bytes = file_input

            # Load document pages as images
            images = load_document_images(file_bytes, resolution=resolution)

            pages_result: list[DocumentPageResult] = []
            page_markdowns: list[str] = []

            for page_idx, page_img in enumerate(images):
                import cv2
                # PaddleOCR expects RGB or path
                rgb_img = cv2.cvtColor(page_img, cv2.COLOR_BGR2RGB)
                result = ocr_engine.ocr(rgb_img, cls=True)

                lines: list[str] = []
                text_lines: list[OCRLineResult] = []

                if result and result[0]:
                    for line in result[0]:
                        box, (text, score) = line
                        lines.append(text)
                        text_lines.append(
                            OCRLineResult(bbox=box, text=text, score=float(score))
                        )

                page_md = "\n".join(lines)
                page_res = DocumentPageResult(
                    page_number=page_idx + 1,
                    text_lines=text_lines,
                    layout_regions=[],
                    tables_markdown=[],
                    page_markdown=page_md,
                )
                pages_result.append(page_res)
                page_markdowns.append(page_md)

                del rgb_img, page_img

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            full_markdown = "\n\n---\n\n".join([pm for pm in page_markdowns if pm.strip()])

            pipeline_name = "paddle_complex_vlm" if mode == "complex-vlm" else self.name

            return DocumentExtractionResponse(
                total_pages=len(pages_result),
                full_markdown=full_markdown,
                pages=pages_result,
                elapsed_ms=round(elapsed_ms, 2),
                metadata=ExtractionMetadata(
                    pipeline_used=pipeline_name,
                    requires_image_input=self.requires_image_input,
                ),
            )
        finally:
            force_garbage_collection_and_trim()
