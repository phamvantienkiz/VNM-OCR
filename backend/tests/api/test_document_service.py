"""Unit tests for DocumentService."""

from pathlib import Path
import pytest
from app.engine.manager import EngineManager
from app.services.document_service import DocumentService


@pytest.fixture(scope="module")
def document_service():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    mgr = EngineManager(models_dir=models_dir, device="cpu")
    mgr.initialize()
    return DocumentService(mgr)


def test_document_service_extract_sample_image(document_service):
    img_dir = Path(__file__).resolve().parents[3] / "img"
    images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No sample images found")

    with open(images[0], "rb") as f:
        file_bytes = f.read()

    response = document_service.extract_document(
        file_bytes=file_bytes,
        extract_tables=True,
    )

    assert response.total_pages == 1
    assert len(response.pages) == 1
    assert response.elapsed_ms > 0
    assert isinstance(response.full_markdown, str)
    assert isinstance(response.pages[0].page_markdown, str)
