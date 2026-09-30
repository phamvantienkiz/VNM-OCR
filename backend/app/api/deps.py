"""FastAPI Dependency Injection Providers."""

from fastapi import Depends
from app.core.config import settings
from app.engine.manager import EngineManager, get_engine_manager
from app.services.ocr_service import OcrService
from app.services.layout_service import LayoutService
from app.services.table_service import TableService
from app.services.document_service import DocumentService


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
    doc_service: DocumentService = Depends(get_document_service),
):
    """Dependency provider for UniversalDocumentDispatcher."""
    from app.services.dispatcher import UniversalDocumentDispatcher

    return UniversalDocumentDispatcher(document_service=doc_service)
