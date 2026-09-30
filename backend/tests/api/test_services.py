"""Unit tests for Service Layer (OCR, Layout, Table)."""

from pathlib import Path
import cv2
import numpy as np
import pytest

from app.engine.manager import EngineManager
from app.services.ocr_service import OcrService
from app.services.layout_service import LayoutService
from app.services.table_service import TableService


@pytest.fixture(scope="module")
def engine_manager():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    mgr = EngineManager(models_dir=models_dir, device="cpu")
    mgr.initialize()
    return mgr


@pytest.fixture
def sample_image_bytes():
    img_dir = Path(__file__).resolve().parents[3] / "img"
    images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No sample images found")

    with open(images[0], "rb") as f:
        return f.read()


def test_ocr_service_process(engine_manager, sample_image_bytes):
    service = OcrService(engine_manager.ocr_engine)
    response = service.process_image(sample_image_bytes)
    assert response.elapsed_ms > 0
    assert isinstance(response.lines, list)

    legacy_resp = service.process_image_legacy(sample_image_bytes)
    assert isinstance(legacy_resp, list)


def test_layout_service_process(engine_manager, sample_image_bytes):
    service = LayoutService(engine_manager.layout_engine)
    response = service.process_image(sample_image_bytes, threshold=0.3)
    assert response.elapsed_ms > 0
    assert isinstance(response.regions, list)


def test_table_service_process(engine_manager, sample_image_bytes):
    service = TableService(engine_manager.table_engine, engine_manager.ocr_engine)
    response = service.process_image(sample_image_bytes, threshold=0.2)
    assert response.elapsed_ms > 0
    assert isinstance(response.markdown, str)
    assert isinstance(response.components, list)
