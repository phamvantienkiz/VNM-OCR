"""Unit tests for OcrEngine."""

from pathlib import Path
import cv2
import numpy as np
import pytest
from app.engine.ocr_engine import OcrEngine


@pytest.fixture(scope="module")
def ocr_engine():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    required_files = ["det.onnx", "cnn.onnx", "encoder.onnx", "decoder.onnx"]
    for f in required_files:
        if not (models_dir / f).exists():
            pytest.skip(f"Required model {f} not found in {models_dir}")
    return OcrEngine(models_dir=models_dir, device="cpu")


def test_sorted_boxes(ocr_engine):
    # Two boxes on the same line (y difference < 10), but box 2 is to the left of box 1
    box1 = np.array([[100, 20], [200, 20], [200, 40], [100, 40]])
    box2 = np.array([[20, 22], [90, 22], [90, 42], [20, 42]])
    box3 = np.array([[20, 80], [150, 80], [150, 100], [20, 100]])  # Lower line

    sorted_bxs = ocr_engine.sorted_boxes([box1, box2, box3])
    # Box 2 should come first (left on line 1), then Box 1 (right on line 1), then Box 3 (line 2)
    assert np.array_equal(sorted_bxs[0], box2)
    assert np.array_equal(sorted_bxs[1], box1)
    assert np.array_equal(sorted_bxs[2], box3)


def test_rotate_crop_image(ocr_engine):
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:40, 10:80] = 255  # White rectangle
    pts = np.array([[10, 20], [80, 20], [80, 40], [10, 40]])

    crop = ocr_engine.get_rotate_crop_image(img, pts)
    assert crop.shape[0] > 0
    assert crop.shape[1] > 0


def test_ocr_engine_predict_sample_image(ocr_engine):
    img_path = Path(__file__).resolve().parents[3] / "img" / "Screenshot 2025-08-28 171633.png"
    if not img_path.exists():
        # Fallback to any existing image in img/
        img_dir = Path(__file__).resolve().parents[3] / "img"
        images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
        if not images:
            pytest.skip("No sample images found in img directory")
        img_path = images[0]

    # Read image safely with unicode path support
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert img is not None

    results = ocr_engine.predict(img)
    assert isinstance(results, list)
    # If image contains text, should have detected boxes
    if len(results) > 0:
        box, (text, score) = results[0]
        assert len(box) == 4
        assert isinstance(text, str)
        assert 0.0 <= score <= 1.0
