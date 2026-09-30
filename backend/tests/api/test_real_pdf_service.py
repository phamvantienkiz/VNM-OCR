"""Service-layer and Unit tests for Real Scanned Administrative PDF."""

from pathlib import Path
import pytest
from app.engine.manager import EngineManager
from app.services.document_service import DocumentService
from app.utils.pdf_utils import is_pdf, load_document_images, render_pdf_to_images


@pytest.fixture(scope="module")
def document_service():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    mgr = EngineManager(models_dir=models_dir, device="cpu")
    mgr.initialize()
    return DocumentService(mgr)


def test_real_pdf_detection_and_rendering(real_pdf_bytes: bytes):
    """Verify PDF magic header detection and OpenCV image rendering."""
    assert is_pdf(real_pdf_bytes) is True

    # Render at default DPI
    images = render_pdf_to_images(real_pdf_bytes, resolution=150)
    assert len(images) == 1
    assert images[0].shape[0] > 1000  # Height ~1754
    assert images[0].shape[1] > 800   # Width ~1241
    assert images[0].shape[2] == 3    # BGR channels


def test_real_pdf_service_extraction(document_service: DocumentService, real_pdf_bytes: bytes):
    """Verify end-to-end DocumentService extraction on real administrative PDF."""
    response = document_service.extract_document(
        file_bytes=real_pdf_bytes,
        extract_tables=True,
        resolution=150,
    )

    assert response.total_pages == 1
    assert len(response.pages) == 1
    assert response.elapsed_ms > 0

    page = response.pages[0]
    assert page.page_number == 1
    assert len(page.text_lines) >= 30
    assert len(page.layout_regions) >= 5

    # Check that headings (##) were generated from layout titles
    assert "##" in page.page_markdown or "##" in response.full_markdown

    # Check key text content
    md_upper = response.full_markdown.upper()
    assert "TRẢNG BÀNG" in md_upper or "UBND" in md_upper
    assert "BÁO CÁO" in md_upper
