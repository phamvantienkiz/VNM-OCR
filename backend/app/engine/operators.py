"""Image Preprocessing Operators for OCR and Document Analysis.

Provides NumPy/OpenCV based image transformations (Resize, Normalize, CHW, NMS)
without legacy dependencies.
"""

from typing import Any
import cv2
import numpy as np


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45) -> list[int]:
    """Perform Non-Maximum Suppression on bounding boxes.

    Args:
        boxes: Array of shape (N, 4) in format [x1, y1, x2, y2].
        scores: Array of shape (N,) containing confidence scores.
        iou_threshold: Intersection over Union threshold for suppression.

    Returns:
        List of retained indices.
    """
    if len(boxes) == 0:
        return []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        ovr = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


class DetResizeForTest:
    """Resize image for DBNet Text Detection while maintaining aspect ratio."""

    def __init__(
        self,
        image_shape: list[int] | None = None,
        limit_side_len: int = 960,
        limit_type: str = "max",
        **kwargs: Any,
    ) -> None:
        self.image_shape = image_shape
        self.limit_side_len = limit_side_len
        self.limit_type = limit_type

    def __call__(self, data: dict[str, Any]) -> dict[str, Any] | None:
        img = data["image"]
        src_h, src_w = img.shape[:2]

        if self.image_shape is not None:
            resize_h, resize_w = self.image_shape
            ratio_h = resize_h / float(src_h)
            ratio_w = resize_w / float(src_w)
        else:
            if self.limit_type == "max":
                limit_side = max(src_h, src_w)
                if limit_side > self.limit_side_len:
                    ratio = float(self.limit_side_len) / limit_side
                else:
                    ratio = 1.0
            else:
                limit_side = min(src_h, src_w)
                if limit_side < self.limit_side_len:
                    ratio = float(self.limit_side_len) / limit_side
                else:
                    ratio = 1.0

            resize_h = int(round(src_h * ratio))
            resize_w = int(round(src_w * ratio))

            # Ensure dimensions are multiples of 32 for CNN stride
            resize_h = max(int(round(resize_h / 32) * 32), 32)
            resize_w = max(int(round(resize_w / 32) * 32), 32)

            ratio_h = resize_h / float(src_h)
            ratio_w = resize_w / float(src_w)

        img = cv2.resize(img, (resize_w, resize_h))
        data["image"] = img
        data["shape"] = np.array([src_h, src_w, ratio_h, ratio_w], dtype=np.float32)
        return data


class NormalizeImage:
    """Normalize image pixel values with mean and standard deviation."""

    def __init__(
        self,
        scale: str | float = "1./255.",
        mean: list[float] | None = None,
        std: list[float] | None = None,
        order: str = "hwc",
        **kwargs: Any,
    ) -> None:
        if isinstance(scale, str):
            if "/" in scale:
                parts = scale.replace(" ", "").split("/")
                self.scale = float(parts[0]) / float(parts[1])
            else:
                self.scale = float(scale)
        else:
            self.scale = float(scale)
        self.mean = np.array(mean if mean is not None else [0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array(std if std is not None else [0.229, 0.224, 0.225], dtype=np.float32)
        self.order = order

    def __call__(self, data: dict[str, Any]) -> dict[str, Any] | None:
        img = data["image"]
        img = (img.astype(np.float32) * self.scale - self.mean) / self.std
        data["image"] = img
        return data


class ToCHWImage:
    """Transpose image dimensions from HWC to CHW."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __call__(self, data: dict[str, Any]) -> dict[str, Any] | None:
        img = data["image"]
        data["image"] = img.transpose((2, 0, 1))
        return data


class KeepKeys:
    """Filter dictionary to retain only specified keys."""

    def __init__(self, keep_keys: list[str], **kwargs: Any) -> None:
        self.keep_keys = keep_keys

    def __call__(self, data: dict[str, Any]) -> list[Any] | None:
        return [data[k] for k in self.keep_keys]


def transform(data: dict[str, Any], ops: list[Any]) -> Any:
    """Apply a sequence of transformation operators to the input data."""
    for op in ops:
        data = op(data)
        if data is None:
            return None
    return data
