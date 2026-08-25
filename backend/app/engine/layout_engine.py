"""Document Layout Analysis Engine using YOLOv10 ONNX.

Performs document layout classification (Text, Title, Table, Figure, Caption, Equation)
and fuses layout regions with OCR bounding boxes.
"""

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
import re
import cv2
import numpy as np

from app.core.constants import (
    DEFAULT_LAYOUT_THRESHOLD,
    LAYOUT_LABELS,
    LAYOUT_ONNX_NAMES,
)
from app.engine.model_loader import load_onnx_session
from app.engine.operators import nms


class LayoutEngine:
    """Document Layout Analysis Engine using YOLOv10."""

    def __init__(
        self,
        model_path: str | Path,
        device: str = "auto",
        device_id: int = 0,
        labels: list[str] | None = None,
    ) -> None:
        self.session, self.run_options = load_onnx_session(model_path, device, device_id)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape[2:4]  # (1024, 1024)
        if None in self.input_shape or self.input_shape[0] <= 0:
            self.target_shape = (1024, 1024)
        else:
            self.target_shape = (int(self.input_shape[0]), int(self.input_shape[1]))

        self.labels = labels or LAYOUT_LABELS
        self.garbage_layouts = ["reference", "header", "footer"]

    def preprocess_image(self, img: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """Preprocess image with letterbox resize, border padding (114), and CHW normalization."""
        src_h, src_w = img.shape[:2]
        target_h, target_w = self.target_shape

        r = min(target_h / float(src_h), target_w / float(src_w))
        new_unpad_w = int(round(src_w * r))
        new_unpad_h = int(round(src_h * r))

        dw = (target_w - new_unpad_w) / 2.0
        dh = (target_h - new_unpad_h) / 2.0

        top = int(round(dh - 0.1))
        bottom = int(round(dh + 0.1))
        left = int(round(dw - 0.1))
        right = int(round(dw + 0.1))

        if img.ndim == 2:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        resized = cv2.resize(img_rgb, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)
        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )

        chw = (padded.astype(np.float32) / 255.0).transpose(2, 0, 1)
        tensor = np.expand_dims(chw, axis=0)

        scale_factor = [src_w / float(new_unpad_w), src_h / float(new_unpad_h), dw, dh]
        return tensor, scale_factor

    def postprocess_outputs(
        self, outputs: np.ndarray, scale_factor: list[float], thr: float = DEFAULT_LAYOUT_THRESHOLD
    ) -> list[dict[str, Any]]:
        """Filter YOLOv10 outputs, reverse letterbox scaling, and apply class-wise NMS."""
        boxes = np.squeeze(outputs)
        if boxes.ndim != 2 or len(boxes) == 0:
            return []

        scores = boxes[:, 4]
        valid_mask = scores > max(thr, 0.08)
        boxes = boxes[valid_mask, :]
        scores = scores[valid_mask]

        if len(boxes) == 0:
            return []

        class_ids = boxes[:, -1].astype(int)
        coords = boxes[:, :4].copy()

        # Reverse padding
        coords[:, 0] -= scale_factor[2]
        coords[:, 2] -= scale_factor[2]
        coords[:, 1] -= scale_factor[3]
        coords[:, 3] -= scale_factor[3]

        # Reverse scaling
        scale_w, scale_h = scale_factor[0], scale_factor[1]
        coords[:, [0, 2]] *= scale_w
        coords[:, [1, 3]] *= scale_h

        unique_classes = np.unique(class_ids)
        keep_indices = []
        for cid in unique_classes:
            c_mask = np.where(class_ids == cid)[0]
            c_boxes = coords[c_mask]
            c_scores = scores[c_mask]
            c_keep = nms(c_boxes, c_scores, 0.45)
            keep_indices.extend(c_mask[c_keep])

        results = []
        for i in keep_indices:
            cid = class_ids[i]
            label_name = self.labels[cid] if cid < len(self.labels) else LAYOUT_ONNX_NAMES.get(cid, "text")
            results.append({
                "type": label_name.lower(),
                "bbox": [float(c) for c in coords[i].tolist()],
                "score": float(scores[i]),
            })

        return results

    def forward(
        self, image_list: list[np.ndarray], thr: float = DEFAULT_LAYOUT_THRESHOLD
    ) -> list[list[dict[str, Any]]]:
        """Detect layout regions for a list of images."""
        all_results = []
        for img in image_list:
            if img is None or img.size == 0:
                all_results.append([])
                continue

            tensor, scale_factor = self.preprocess_image(img)
            outputs = self.session.run(None, {self.input_name: tensor}, self.run_options)
            regions = self.postprocess_outputs(outputs[0], scale_factor, thr=thr)
            all_results.append(regions)

        return all_results

    @staticmethod
    def find_overlapped_with_threshold(
        box: dict[str, Any], regions: list[dict[str, Any]], thr: float = 0.4
    ) -> int | None:
        """Find the index of the region with the highest overlap ratio above threshold."""
        best_idx = None
        best_overlap = 0.0

        bx0, by0, bx1, by1 = box["bbox"][0], box["bbox"][1], box["bbox"][2], box["bbox"][3]
        b_area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
        if b_area <= 0:
            return None

        for idx, reg in enumerate(regions):
            rx0, ry0, rx1, ry1 = reg["bbox"][0], reg["bbox"][1], reg["bbox"][2], reg["bbox"][3]
            inter_x0 = max(bx0, rx0)
            inter_y0 = max(by0, ry0)
            inter_x1 = min(bx1, rx1)
            inter_y1 = min(by1, ry1)

            if inter_x1 > inter_x0 and inter_y1 > inter_y0:
                inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
                overlap_ratio = inter_area / b_area
                if overlap_ratio >= thr and overlap_ratio > best_overlap:
                    best_overlap = overlap_ratio
                    best_idx = idx

        return best_idx

    def fuse_with_ocr(
        self,
        image_list: list[np.ndarray],
        ocr_results: list[list[dict[str, Any]]],
        thr: float = 0.4,
        drop_garbage: bool = True,
    ) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
        """Fuse Document Layout Analysis regions with OCR text boxes to assign layout types."""
        layouts = self.forward(image_list, thr=thr)
        fused_boxes = []
        page_layouts = []

        for pn, lts in enumerate(layouts):
            bxs = deepcopy(ocr_results[pn])
            page_h = image_list[pn].shape[0]

            for b in bxs:
                b["page_number"] = pn
                matched_idx = self.find_overlapped_with_threshold(b, lts, thr=thr)
                if matched_idx is not None:
                    matched_layout = lts[matched_idx]
                    b["layout_type"] = matched_layout["type"]
                    b["layout_score"] = matched_layout["score"]
                else:
                    b["layout_type"] = "text"
                    b["layout_score"] = 1.0

            if drop_garbage:
                # Filter out pure page numbers / headers at edges
                cleaned = []
                for b in bxs:
                    text = b.get("text", "").strip()
                    by0 = b["bbox"][1]
                    by1 = b["bbox"][3]
                    # Page numbers or header/footer patterns
                    if re.match(r"^[0-9]{1,3}\s*/\s*[0-9]{1,3}$", text) or re.match(r"^[0-9]{1,3}$", text):
                        if by0 < page_h * 0.08 or by1 > page_h * 0.92:
                            continue
                    cleaned.append(b)
                bxs = cleaned

            fused_boxes.extend(bxs)
            page_layouts.append(lts)

        return fused_boxes, page_layouts

    def __call__(
        self, image_list: list[np.ndarray], thr: float = DEFAULT_LAYOUT_THRESHOLD
    ) -> list[list[dict[str, Any]]]:
        """Callable interface returning detected layout regions for image list."""
        return self.forward(image_list, thr=thr)
