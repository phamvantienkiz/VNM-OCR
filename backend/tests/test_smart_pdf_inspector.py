"""Unit tests for SmartPDFInspector and UniversalDocumentDispatcher (Phase 4)."""

import io
from pathlib import Path
from PIL import Image
import pytest
from app.services.inspector import SmartPDFInspector, PageType, PDFPageProfile
from app.services.dispatcher import UniversalDocumentDispatcher
from app.services.document_service import DocumentService
from app.engine.manager import get_engine_manager


def test_classify_document_digital():
    """Verify document with pure digital pages is classified as DIGITAL_DOCUMENT."""
    profiles = [
        PDFPageProfile(page_num=1, char_count=500, raster_image_count=0, scs_score=0.0, page_type=PageType.DIGITAL_DOCUMENT),
        PDFPageProfile(page_num=2, char_count=800, raster_image_count=0, scs_score=0.0, page_type=PageType.DIGITAL_DOCUMENT),
    ]
    doc_type = SmartPDFInspector.classify_document(profiles)
    assert doc_type == PageType.DIGITAL_DOCUMENT


def test_classify_document_scanned():
    """Verify document with high SCS score is classified as SCANNED_DOCUMENT."""
    profiles = [
        PDFPageProfile(page_num=1, char_count=0, raster_image_count=1, scs_score=1.0, page_type=PageType.SCANNED_DOCUMENT),
        PDFPageProfile(page_num=2, char_count=10, raster_image_count=1, scs_score=0.8, page_type=PageType.SCANNED_DOCUMENT),
    ]
    doc_type = SmartPDFInspector.classify_document(profiles)
    assert doc_type == PageType.SCANNED_DOCUMENT


def test_classify_document_corrupted():
    """Verify corrupted vector is detected and prioritized."""
    profiles = [
        PDFPageProfile(page_num=1, char_count=200, raster_image_count=0, scs_score=0.1, page_type=PageType.CORRUPTED_VECTOR),
    ]
    doc_type = SmartPDFInspector.classify_document(profiles)
    assert doc_type == PageType.CORRUPTED_VECTOR


def test_dispatcher_with_image():
    """Verify dispatcher processes image files directly."""
    models_dir = Path(__file__).resolve().parents[1] / "models"
    mgr = get_engine_manager(models_dir=models_dir)
    doc_svc = DocumentService(engine_manager=mgr)
    dispatcher = UniversalDocumentDispatcher(document_service=doc_svc)

    pil_img = Image.new("RGB", (64, 64), color=(200, 200, 200))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    resp, meta = dispatcher.dispatch(buf)
    assert resp.total_pages == 1
    assert meta["is_pdf"] is False
    assert meta["pipeline_used"] == "heavy_onnx_pipeline"
