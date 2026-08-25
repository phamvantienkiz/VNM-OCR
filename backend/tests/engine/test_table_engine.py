"""Unit tests for TableEngine."""

from pathlib import Path
import cv2
import numpy as np
import pytest
from app.engine.table_engine import TableEngine


@pytest.fixture(scope="module")
def table_engine():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    tsr_model = models_dir / "tsr.onnx"
    if not tsr_model.exists():
        pytest.skip(f"Model {tsr_model} not found")
    return TableEngine(model_path=tsr_model, device="cpu")


def test_construct_markdown_grid():
    components = [
        {"type": "table column", "bbox": [0, 0, 50, 100], "score": 0.9},
        {"type": "table column", "bbox": [50, 0, 100, 100], "score": 0.9},
        {"type": "table row", "bbox": [0, 0, 100, 30], "score": 0.9},
        {"type": "table row", "bbox": [0, 30, 100, 60], "score": 0.9},
        {"type": "table row", "bbox": [0, 60, 100, 100], "score": 0.9},
    ]
    ocr_boxes = [
        {"bbox": [5, 5, 45, 25], "text": "STT"},
        {"bbox": [55, 5, 95, 25], "text": "Tên"},
        {"bbox": [5, 35, 45, 55], "text": "1"},
        {"bbox": [55, 35, 95, 55], "text": "Sản phẩm A"},
        {"bbox": [5, 65, 45, 95], "text": "2"},
        {"bbox": [55, 65, 95, 95], "text": "Sản phẩm B"},
    ]

    md = TableEngine.construct_markdown(components, ocr_boxes)
    assert "| STT | Tên |" in md
    assert "| --- | --- |" in md
    assert "| 1 | Sản phẩm A |" in md
    assert "| 2 | Sản phẩm B |" in md


def test_construct_markdown_fallback():
    # When no TSR components detected
    components = []
    ocr_boxes = [
        {"bbox": [10, 10, 50, 30], "text": "Mã"},
        {"bbox": [60, 10, 100, 30], "text": "Giá"},
        {"bbox": [10, 40, 50, 60], "text": "SP01"},
        {"bbox": [60, 40, 100, 60], "text": "100.000"},
    ]
    md = TableEngine.construct_markdown(components, ocr_boxes)
    assert "| Mã | Giá |" in md
    assert "| --- | --- |" in md
    assert "| SP01 | 100.000 |" in md


def test_table_recognize_structure_sample(table_engine):
    img_dir = Path(__file__).resolve().parents[3] / "img"
    images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No sample images found")

    with open(images[0], "rb") as f:
        img_bytes = f.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert img is not None

    components = table_engine.recognize_structure(img, thr=0.2)
    assert isinstance(components, list)
