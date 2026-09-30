"""Unit tests for operators and postprocess modules."""

import numpy as np
from app.engine.operators import (
    nms,
    DetResizeForTest,
    NormalizeImage,
    ToCHWImage,
    KeepKeys,
    transform,
)
from app.engine.postprocess import DBPostProcess


def test_nms_suppression():
    boxes = np.array([
        [10.0, 10.0, 50.0, 50.0],
        [12.0, 12.0, 52.0, 52.0],  # Overlapping with first box
        [100.0, 100.0, 150.0, 150.0],  # Non-overlapping
    ])
    scores = np.array([0.9, 0.7, 0.85])
    keep = nms(boxes, scores, iou_threshold=0.5)

    assert 0 in keep
    assert 2 in keep
    assert 1 not in keep  # Suppressed


def test_det_resize_for_test():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    resize_op = DetResizeForTest(limit_side_len=960, limit_type="max")
    data = resize_op({"image": img})

    resized_img = data["image"]
    shape = data["shape"]
    assert resized_img.shape[0] % 32 == 0
    assert resized_img.shape[1] % 32 == 0
    assert shape[0] == 480
    assert shape[1] == 640


def test_normalize_and_chw():
    img = np.ones((64, 64, 3), dtype=np.uint8) * 255
    data = {"image": img}

    ops = [
        NormalizeImage(),
        ToCHWImage(),
        KeepKeys(keep_keys=["image"]),
    ]
    res = transform(data, ops)
    out_img = res[0]

    assert out_img.shape == (3, 64, 64)
    assert out_img.dtype == np.float32


def test_db_postprocess_synthetic():
    post = DBPostProcess(thresh=0.3, box_thresh=0.5)
    # Create a synthetic probability map with a high-confidence rectangle
    pred = np.zeros((1, 1, 100, 100), dtype=np.float32)
    pred[0, 0, 20:60, 20:80] = 0.95
    shape_list = np.array([[100, 100, 1.0, 1.0]])

    results = post({"maps": pred}, shape_list)
    assert len(results) == 1
    assert len(results[0]["points"]) >= 1
    box = results[0]["points"][0]
    assert box.shape == (4, 2)
