"""VNMOCRExtractor — Vietnamese OCR extraction pipeline wrapper.

Wraps the existing ONNX-based pipeline (DBNet + YOLOv10 + YOLOv8 + VietOCR Seq2Seq)
for high-quality Vietnamese document OCR through the unified Extractor interface.
"""

import logging
import time
from typing import Any, BinaryIO

from app.engine.manager import EngineManager
from app.schemas.document import DocumentExtractionResponse, ExtractionMetadata
from app.services.document_service import DocumentService
from app.services.extractors.base import BaseExtractor
from app.utils.memory_utils import force_garbage_collection_and_trim

logger = logging.getLogger(__name__)


class VNMOCRExtractor(BaseExtractor):
    """Vietnamese OCR Extractor using the full ONNX neural pipeline.

    Pipeline: DBNet (det) → YOLOv10 (layout) → YOLOv8 (tsr) → VietOCR Seq2Seq
    Peak RAM: ~1.5GB during inference.
    """

    def __init__(self, engine_manager: EngineManager) -> None:
        self._document_service = DocumentService(engine_manager=engine_manager)

    @property
    def name(self) -> str:
        return "vnm_ocr"

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
        start_time = time.perf_counter()
        try:
            response = self._document_service.extract_document(
                file_input=file_input,
                extract_tables=extract_tables,
                resolution=resolution,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            response.metadata = ExtractionMetadata(
                pipeline_used=self.name,
                requires_image_input=self.requires_image_input,
                is_vector_recovery=kwargs.get("is_vector_recovery", False),
            )
            response.elapsed_ms = round(elapsed_ms, 2)
            logger.info("VNMOCRExtractor: %d pages, %.2f ms", response.total_pages, elapsed_ms)
            return response
        finally:
            force_garbage_collection_and_trim()
