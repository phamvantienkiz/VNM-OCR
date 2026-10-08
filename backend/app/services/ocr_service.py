"""OCR Service Layer."""

import time
import logging
from typing import Any, BinaryIO
import numpy as np

from app.engine.ocr_engine import OcrEngine
from app.schemas.ocr import OCRLineResult, OCRResponse
from app.utils.image_utils import decode_image_bytes, decode_image_file

logger = logging.getLogger(__name__)


class OcrService:
    """Service layer orchestrating OCR operations."""

    def __init__(self, ocr_engine: OcrEngine) -> None:
        self.engine = ocr_engine

    def process_image_file(self, file_obj: BinaryIO) -> OCRResponse:
        """Run OCR directly on a file-like object and return typed Pydantic response."""
        start_time = time.perf_counter()
        img = decode_image_file(file_obj)

        raw_results = self.engine.predict(img)
        lines: list[OCRLineResult] = []

        for box, (text, score) in raw_results:
            lines.append(
                OCRLineResult(
                    bbox=box,
                    text=text,
                    score=float(score),
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OCRResponse(
            lines=lines,
            total_lines=len(lines),
            elapsed_ms=round(elapsed_ms, 2),
        )

    def process_image(self, image_input: bytes | BinaryIO) -> OCRResponse:
        """Run OCR on image bytes or file-like object and return typed Pydantic response."""
        if hasattr(image_input, "read"):
            return self.process_image_file(image_input)

        start_time = time.perf_counter()
        img = decode_image_bytes(image_input)

        raw_results = self.engine.predict(img)
        lines: list[OCRLineResult] = []

        for box, (text, score) in raw_results:
            lines.append(
                OCRLineResult(
                    bbox=box,
                    text=text,
                    score=float(score),
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OCRResponse(
            lines=lines,
            total_lines=len(lines),
            elapsed_ms=round(elapsed_ms, 2),
        )

    def process_image_legacy(self, image_input: bytes | BinaryIO) -> list[list[Any]]:
        """Run OCR and return legacy nested array format compatible with existing Web UI.

        Format: [ [ [[x1, y1], [x2, y2], [x3, y3], [x4, y4]], [text, score] ], ... ]
        """
        if hasattr(image_input, "read"):
            img = decode_image_file(image_input)
        else:
            img = decode_image_bytes(image_input)

        raw_results = self.engine.predict(img)

        legacy_results: list[list[Any]] = []
        for box, (text, score) in raw_results:
            legacy_results.append([box, [text, float(score)]])

        return legacy_results
