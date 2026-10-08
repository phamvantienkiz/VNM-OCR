"""Integration Tests for /extract/auto dispatching across SCANNED, DIGITAL, CORRUPTED, COMPLEX classifications."""

from unittest.mock import patch, MagicMock
import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.inspector import PageType, PDFPageProfile
from app.schemas.document import DocumentExtractionResponse, ExtractionMetadata

client = TestClient(app)


def _create_sample_png() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_auto_scanned_image():
    """Verify image upload is classified as SCANNED and routed to VNM OCR."""
    png_bytes = _create_sample_png()
    resp = client.post(
        "/api/v1/extract/auto",
        files={"file": ("scan.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["pipeline_used"] == "vnm_ocr"
    assert data["metadata"]["classification"] == "SCANNED_DOCUMENT"


def test_extract_auto_digital_pdf_routing():
    """Verify DIGITAL_DOCUMENT classification routes to NativePDFExtractor."""
    fake_profiles = [
        PDFPageProfile(
            page_num=1,
            char_count=500,
            raster_image_count=0,
            scs_score=0.0,
            page_type=PageType.DIGITAL_DOCUMENT,
        )
    ]
    with patch("app.services.inspector.SmartPDFInspector.inspect", return_value=fake_profiles), \
         patch("app.services.inspector.SmartPDFInspector.classify_document", return_value=PageType.DIGITAL_DOCUMENT), \
         patch("app.services.extractors.native.NativePDFExtractor.extract") as mock_native_extract:

        mock_native_extract.return_value = DocumentExtractionResponse(
            total_pages=1,
            full_markdown="Digital text extracted",
            pages=[],
            elapsed_ms=12.5,
            metadata=ExtractionMetadata(
                pipeline_used="native_pdf",
                requires_image_input=False,
            ),
        )

        resp = client.post(
            "/api/v1/extract/auto",
            files={"file": ("digital.pdf", b"%PDF-1.4 dummy digital content", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["pipeline_used"] == "native_pdf"
        assert data["metadata"]["classification"] == "DIGITAL_DOCUMENT"
        assert mock_native_extract.called


def test_extract_auto_corrupted_vector_routing():
    """Verify CORRUPTED_VECTOR classification routes to VNM OCR with is_vector_recovery=True."""
    fake_profiles = [
        PDFPageProfile(
            page_num=1,
            char_count=200,
            raster_image_count=0,
            scs_score=0.1,
            page_type=PageType.CORRUPTED_VECTOR,
        )
    ]
    with patch("app.services.inspector.SmartPDFInspector.inspect", return_value=fake_profiles), \
         patch("app.services.inspector.SmartPDFInspector.classify_document", return_value=PageType.CORRUPTED_VECTOR), \
         patch("app.services.extractors.vnm.VNMOCRExtractor.extract") as mock_vnm_extract:

        mock_vnm_extract.return_value = DocumentExtractionResponse(
            total_pages=1,
            full_markdown="Recovered text",
            pages=[],
            elapsed_ms=85.0,
            metadata=ExtractionMetadata(
                pipeline_used="vnm_ocr",
                requires_image_input=True,
                is_vector_recovery=True,
            ),
        )

        resp = client.post(
            "/api/v1/extract/auto",
            files={"file": ("broken_fonts.pdf", b"%PDF-1.4 dummy corrupted content", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["pipeline_used"] == "vnm_ocr"
        assert data["metadata"]["classification"] == "CORRUPTED_VECTOR"
        assert data["metadata"]["is_vector_recovery"] is True
        assert mock_vnm_extract.called
        kwargs = mock_vnm_extract.call_args.kwargs
        assert kwargs.get("is_vector_recovery") is True


def test_extract_auto_complex_routing():
    """Verify COMPLEX_DOCUMENT classification routes to VNM OCR."""
    fake_profiles = [
        PDFPageProfile(
            page_num=1,
            char_count=300,
            raster_image_count=0,
            scs_score=0.1,
            has_math=True,
            page_type=PageType.COMPLEX_DOCUMENT,
        )
    ]
    with patch("app.services.inspector.SmartPDFInspector.inspect", return_value=fake_profiles), \
         patch("app.services.inspector.SmartPDFInspector.classify_document", return_value=PageType.COMPLEX_DOCUMENT), \
         patch("app.services.extractors.vnm.VNMOCRExtractor.extract") as mock_vnm_extract:

        mock_vnm_extract.return_value = DocumentExtractionResponse(
            total_pages=1,
            full_markdown="Complex layout extracted",
            pages=[],
            elapsed_ms=110.0,
            metadata=ExtractionMetadata(
                pipeline_used="vnm_ocr",
                requires_image_input=True,
            ),
        )

        resp = client.post(
            "/api/v1/extract/auto",
            files={"file": ("complex.pdf", b"%PDF-1.4 dummy math content", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["pipeline_used"] == "vnm_ocr"
        assert data["metadata"]["classification"] == "COMPLEX_DOCUMENT"
        assert mock_vnm_extract.called
