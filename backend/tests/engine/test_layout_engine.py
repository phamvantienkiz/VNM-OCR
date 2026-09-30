"""Unit tests for LayoutEngine."""

from pathlib import Path
import cv2
import numpy as np
import pytest
from app.engine.layout_engine import LayoutEngine


@pytest.fixture(scope="module")
def layout_engine():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    layout_model = models_dir / "layout.onnx"
    if not layout_model.exists():
        pytest.skip(f"Model {layout_model} not found")
    return LayoutEngine(model_path=layout_model, device="cpu")


def test_layout_preprocess_shape(layout_engine):
    img = np.zeros((600, 800, 3), dtype=np.uint8)
    tensor, scale_factor = layout_engine.preprocess_image(img)

    assert tensor.shape == (1, 3, 1024, 1024)
    assert len(scale_factor) == 4


def test_layout_forward_sample_image(layout_engine):
    img_dir = Path(__file__).resolve().parents[3] / "img"
    images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No sample images found")

    with open(images[0], "rb") as f:
        img_bytes = f.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert img is not None

    regions_list = layout_engine.forward([img], thr=0.3)
    assert len(regions_list) == 1
    regions = regions_list[0]
    assert isinstance(regions, list)
    for reg in regions:
        assert "type" in reg
        assert "bbox" in reg
        assert len(reg["bbox"]) == 4
        assert 0.0 <= reg["score"] <= 1.0


def test_find_overlapped_with_threshold(layout_engine):
    box = {"bbox": [10.0, 10.0, 50.0, 50.0]}
    regions = [
        {"bbox": [100.0, 100.0, 200.0, 200.0], "type": "figure", "score": 0.9},
        {"bbox": [5.0, 5.0, 55.0, 55.0], "type": "table", "score": 0.85},  # Covers box completely
    ]

    matched_idx = layout_engine.find_overlapped_with_threshold(box, regions, thr=0.4)
    assert matched_idx == 1
