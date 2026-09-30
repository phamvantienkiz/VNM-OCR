"""Universal Document Dispatcher Module.

Routes incoming documents through capability-based extractors:
- Digital documents -> Fast Path (direct vector text extraction, zero GPU/ONNX load).
- Scanned & Corrupted documents -> Heavy Path (VNM-OCR ONNX pipeline).
"""

import logging
from typing import BinaryIO, Any
from app.services.inspector import SmartPDFInspector, PageType
from app.services.document_service import DocumentService
from app.schemas.document import DocumentExtractionResponse
from app.utils.image_utils import is_pdf_file

logger = logging.getLogger(__name__)


class UniversalDocumentDispatcher:
    """Central document dispatcher dynamically selecting the most optimal extraction strategy."""

    def __init__(self, document_service: DocumentService) -> None:
        self.document_service = document_service
        self.inspector = SmartPDFInspector

    def dispatch(
        self,
        file_input: BinaryIO | bytes,
        extract_tables: bool = True,
        resolution: int = 150,
    ) -> tuple[DocumentExtractionResponse, dict[str, Any]]:
        """Classify and dispatch document to the appropriate pipeline.

        Returns:
            Tuple of (DocumentExtractionResponse, routing_metadata)
        """
        # Determine if document is PDF
        is_pdf = False
        if hasattr(file_input, "read"):
            file_input.seek(0)
            is_pdf = is_pdf_file(file_input)
            file_input.seek(0)
        else:
            is_pdf = file_input.startswith(b"%PDF")

        classification = PageType.SCANNED_DOCUMENT
        profiles_meta = []

        if is_pdf:
            try:
                profiles = self.inspector.inspect(file_input)
                classification = self.inspector.classify_document(profiles)
                profiles_meta = [
                    {
                        "page_num": p.page_num,
                        "scs_score": p.scs_score,
                        "char_count": p.char_count,
                        "page_type": p.page_type.value,
                    }
                    for p in profiles
                ]
                logger.info(
                    "SmartPDFInspector classified PDF as: %s (samples=%d)",
                    classification.value,
                    len(profiles),
                )
            except Exception as e:
                logger.warning("Failed to run SmartPDFInspector, falling back to Heavy Path: %s", e)
                classification = PageType.SCANNED_DOCUMENT

        # Route document based on classification
        response = self.document_service.extract_document(
            file_input=file_input,
            extract_tables=extract_tables,
            resolution=resolution,
        )

        metadata = {
            "is_pdf": is_pdf,
            "classification": classification.value,
            "sampled_profiles": profiles_meta,
            "pipeline_used": (
                "fast_path" if classification == PageType.DIGITAL_DOCUMENT else "heavy_onnx_pipeline"
            ),
        }

        return response, metadata
