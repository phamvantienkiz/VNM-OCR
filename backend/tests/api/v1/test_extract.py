"""Unit and Integration Tests for Phase 6 Explicit Extract Endpoints (/extract/*)."""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_sample_png() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_docling_unavailable_returns_501():
    """Verify calling /extract/docling returns 501 when optional docling is not installed."""
    response = client.post(
        "/api/v1/extract/docling",
        files={"file": ("test.docx", b"dummy docx content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 501
    assert "DoclingUniversalExtractor" in response.json()["detail"]


def test_extract_paddle_ocr_unavailable_returns_501():
    """Verify calling /extract/paddle/ocr returns 501 when optional paddleocr is not installed."""
    response = client.post(
        "/api/v1/extract/paddle/ocr",
        files={"file": ("test.png", _create_sample_png(), "image/png")},
    )
    assert response.status_code == 501
    assert "PaddleOCRExtractor" in response.json()["detail"]


def test_extract_paddle_complex_vlm_unavailable_returns_501():
    """Verify calling /extract/paddle/complex-vlm returns 501 when optional paddleocr is not installed."""
    response = client.post(
        "/api/v1/extract/paddle/complex-vlm",
        files={"file": ("test.png", _create_sample_png(), "image/png")},
    )
    assert response.status_code == 501
    assert "PaddleOCRExtractor" in response.json()["detail"]


def test_extract_endpoints_no_file():
    """Verify endpoints validate file presence."""
    for endpoint in ["/api/v1/extract/auto", "/api/v1/extract/native/pdf", "/api/v1/extract/vnm"]:
        resp = client.post(endpoint)
        assert resp.status_code == 422  # Missing required multipart field


def test_extract_vnm_and_auto_with_image():
    """Verify /extract/vnm and /extract/auto execute successfully and include metadata."""
    png_bytes = _create_sample_png()

    # Test /extract/vnm
    resp_vnm = client.post(
        "/api/v1/extract/vnm",
        files={"file": ("sample.png", png_bytes, "image/png")},
    )
    assert resp_vnm.status_code == 200, resp_vnm.text
    data_vnm = resp_vnm.json()
    assert data_vnm["total_pages"] == 1
    assert data_vnm["metadata"]["pipeline_used"] == "vnm_ocr"
    assert data_vnm["metadata"]["requires_image_input"] is True

    # Test /extract/auto
    resp_auto = client.post(
        "/api/v1/extract/auto",
        files={"file": ("sample.png", png_bytes, "image/png")},
    )
    assert resp_auto.status_code == 200, resp_auto.text
    data_auto = resp_auto.json()
    assert data_auto["total_pages"] == 1
    assert data_auto["metadata"]["pipeline_used"] == "vnm_ocr"
    assert "classification" in data_auto["metadata"]
