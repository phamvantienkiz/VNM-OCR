"""FastAPI Dependency Injection Providers."""

from typing import TYPE_CHECKING
from fastapi import Depends
from app.core.config import settings
from app.engine.manager import EngineManager, get_engine_manager
from app.services.ocr_service import OcrService
from app.services.layout_service import LayoutService
from app.services.table_service import TableService
from app.services.document_service import DocumentService

if TYPE_CHECKING:
    from app.services.dispatcher import UniversalDocumentDispatcher
    from app.services.extractors.native import NativePDFExtractor
    from app.services.extractors.vnm import VNMOCRExtractor
    from app.services.extractors.docling import DoclingUniversalExtractor
    from app.services.extractors.paddle import PaddleOCRExtractor


def get_engine_manager_dep() -> EngineManager:
    """Dependency provider returning the singleton EngineManager."""
    return get_engine_manager(models_dir=settings.resolved_models_dir)


def get_ocr_service(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> OcrService:
    """Dependency provider for OcrService."""
    return OcrService(ocr_engine=manager.ocr_engine)


def get_layout_service(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> LayoutService:
    """Dependency provider for LayoutService."""
    return LayoutService(layout_engine=manager.layout_engine)


def get_table_service(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> TableService:
    """Dependency provider for TableService."""
    return TableService(
        table_engine=manager.table_engine,
        ocr_engine=manager.ocr_engine,
    )


def get_document_service(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> DocumentService:
    """Dependency provider for DocumentService."""
    return DocumentService(engine_manager=manager)


def get_dispatcher_service(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> "UniversalDocumentDispatcher":
    """Dependency provider for UniversalDocumentDispatcher (backward-compatible alias)."""
    from app.services.dispatcher import UniversalDocumentDispatcher

    return UniversalDocumentDispatcher(engine_manager=manager)


# ── Phase 6: Extractor DI Providers ─────────────────────────────────


def get_native_extractor() -> "NativePDFExtractor":
    """DI provider for NativePDFExtractor (no engine needed)."""
    from app.services.extractors.native import NativePDFExtractor

    return NativePDFExtractor()


def get_vnm_extractor(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> "VNMOCRExtractor":
    """DI provider for VNMOCRExtractor (needs EngineManager for ONNX models)."""
    from app.services.extractors.vnm import VNMOCRExtractor

    return VNMOCRExtractor(engine_manager=manager)


def get_docling_extractor() -> "DoclingUniversalExtractor":
    """DI provider for DoclingUniversalExtractor (optional dependency)."""
    from app.services.extractors.docling import DoclingUniversalExtractor

    return DoclingUniversalExtractor()


def get_paddle_extractor() -> "PaddleOCRExtractor":
    """DI provider for PaddleOCRExtractor (optional dependency)."""
    from app.services.extractors.paddle import PaddleOCRExtractor

    return PaddleOCRExtractor()


def get_dispatcher(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> "UniversalDocumentDispatcher":
    """DI provider for the refactored UniversalDocumentDispatcher."""
    from app.services.dispatcher import UniversalDocumentDispatcher

    return UniversalDocumentDispatcher(engine_manager=manager)
