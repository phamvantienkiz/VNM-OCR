"""Universal Document Dispatcher Module.

Routes incoming documents through capability-based extractors using the
Strategy Pattern. SmartPDFInspector classifies → select best extractor → execute.
"""

import io
import logging
from typing import Any, BinaryIO

from app.engine.manager import EngineManager
from app.services.inspector import SmartPDFInspector, PageType
from app.services.extractors.base import BaseExtractor
from app.services.extractors.native import NativePDFExtractor
from app.services.extractors.vnm import VNMOCRExtractor
from app.services.extractors.docling import DoclingUniversalExtractor
from app.schemas.document import DocumentExtractionResponse, ExtractionMetadata
from app.utils.image_utils import is_pdf_file

logger = logging.getLogger(__name__)


class UniversalDocumentDispatcher:
    """Routes documents to the optimal extractor based on SmartPDFInspector analysis."""

    def __init__(
        self,
        engine_manager: EngineManager | None = None,
        document_service: Any = None,
    ) -> None:
        if engine_manager is None and document_service is not None:
            engine_manager = getattr(document_service, "engine_manager", None)
        self._engine_manager = engine_manager
        self._native_extractor = NativePDFExtractor()
        self._vnm_extractor = VNMOCRExtractor(engine_manager=engine_manager)
        self._docling_extractor = DoclingUniversalExtractor()

    def _select_extractor(
        self, classification: PageType
    ) -> tuple[BaseExtractor, dict[str, Any]]:
        """Select the best extractor and extra kwargs based on classification."""
        if classification == PageType.DIGITAL_DOCUMENT:
            return self._native_extractor, {}
        elif classification == PageType.CORRUPTED_VECTOR:
            return self._vnm_extractor, {"is_vector_recovery": True}
        else:
            # SCANNED_DOCUMENT, COMPLEX_DOCUMENT → VNM OCR pipeline
            return self._vnm_extractor, {}

    def dispatch(
        self,
        file_input: BinaryIO | bytes,
        extract_tables: bool = True,
        resolution: int = 150,
        filename: str | None = None,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        """Classify → select extractor → execute → return response with metadata."""
        # 0. Route Office formats directly
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in self._docling_extractor.supported_extensions:
                return self._docling_extractor.extract(
                    file_input,
                    extract_tables=extract_tables,
                    filename=filename,
                    **kwargs,
                )
        # Detect PDF
        is_pdf = False
        if hasattr(file_input, "read"):
            file_input.seek(0)
            is_pdf = is_pdf_file(file_input)
            file_input.seek(0)
        else:
            is_pdf = file_input.startswith(b"%PDF")

        classification = PageType.SCANNED_DOCUMENT

        if is_pdf:
            try:
                profiles = SmartPDFInspector.inspect(file_input)
                classification = SmartPDFInspector.classify_document(profiles)
                logger.info("SmartPDFInspector → %s", classification.value)
            except Exception as e:
                logger.warning("Inspector failed, fallback Heavy Path: %s", e)

        extractor, extra_kwargs = self._select_extractor(classification)

        if hasattr(file_input, "seek"):
            file_input.seek(0)

        response = extractor.extract(
            file_input,
            extract_tables=extract_tables,
            resolution=resolution,
            **extra_kwargs,
        )

        # Enrich metadata with classification
        if response.metadata:
            response.metadata.classification = classification.value
        else:
            response.metadata = ExtractionMetadata(
                pipeline_used=extractor.name,
                classification=classification.value,
            )

        return response
