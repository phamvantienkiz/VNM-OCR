"""Table Structure Recognition Engine (TSR) using YOLOv8 ONNX.

Extracts table grid structure (rows, columns, headers, spanning cells)
and reconstructs structured tables into Markdown.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any
import cv2
import numpy as np

from app.core.constants import DEFAULT_TSR_THRESHOLD, TSR_LABELS
from app.engine.model_loader import load_onnx_session
from app.engine.operators import nms


class TableEngine:
    """Table Structure Recognition and Markdown Table Builder using YOLOv8."""

    def __init__(
        self,
        model_path: str | Path,
        device: str = "auto",
        device_id: int = 0,
        labels: list[str] | None = None,
    ) -> None:
        self.session, self.run_options = load_onnx_session(model_path, device, device_id)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape[2:4]
        if None in self.input_shape or self.input_shape[0] <= 0:
            self.target_shape = (640, 640)
        else:
            self.target_shape = (int(self.input_shape[0]), int(self.input_shape[1]))

        self.labels = labels or TSR_LABELS

    def preprocess_image(self, img: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """Preprocess cropped table image with letterbox resize, border padding (114), and CHW normalization."""
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
        self, outputs: np.ndarray, scale_factor: list[float], thr: float = DEFAULT_TSR_THRESHOLD
    ) -> list[dict[str, Any]]:
        """Process YOLOv8 TSR outputs: transpose (8400, 11), convert xywh -> xyxy, unpad, and run NMS."""
        raw = np.squeeze(outputs)
        if raw.ndim != 2:
            return []

        # YOLOv8 format: (11, 8400) -> transpose to (8400, 11)
        if raw.shape[0] < raw.shape[1]:
            boxes_all = raw.T
        else:
            boxes_all = raw

        # boxes_all format: [cx, cy, w, h, class_0_score, class_1_score, ...]
        coords_xywh = boxes_all[:, :4]
        class_scores = boxes_all[:, 4:]

        max_scores = np.max(class_scores, axis=1)
        valid_mask = max_scores > max(thr, 0.05)

        if not np.any(valid_mask):
            return []

        coords_xywh = coords_xywh[valid_mask]
        class_scores = class_scores[valid_mask]
        max_scores = max_scores[valid_mask]
        class_ids = np.argmax(class_scores, axis=1)

        # Convert xywh to xyxy
        cx = coords_xywh[:, 0]
        cy = coords_xywh[:, 1]
        w = coords_xywh[:, 2]
        h = coords_xywh[:, 3]

        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0

        # Reverse padding
        x1 -= scale_factor[2]
        x2 -= scale_factor[2]
        y1 -= scale_factor[3]
        y2 -= scale_factor[3]

        # Reverse scaling
        scale_w, scale_h = scale_factor[0], scale_factor[1]
        x1 *= scale_w
        x2 *= scale_w
        y1 *= scale_h
        y2 *= scale_h

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        # Class-wise NMS
        unique_classes = np.unique(class_ids)
        keep_indices = []
        for cid in unique_classes:
            c_mask = np.where(class_ids == cid)[0]
            c_boxes = boxes_xyxy[c_mask]
            c_scores = max_scores[c_mask]
            c_keep = nms(c_boxes, c_scores, 0.3)
            keep_indices.extend(c_mask[c_keep])

        results = []
        for i in keep_indices:
            cid = class_ids[i]
            label_name = self.labels[cid] if cid < len(self.labels) else "table row"
            score_val = float(np.clip(max_scores[i], 0.0, 1.0))
            results.append({
                "type": label_name.lower(),
                "bbox": [float(c) for c in boxes_xyxy[i].tolist()],
                "score": score_val,
            })

        return results

    def recognize_structure(
        self, table_img: np.ndarray, thr: float = DEFAULT_TSR_THRESHOLD
    ) -> list[dict[str, Any]]:
        """Recognize table structural components on a cropped table image."""
        if table_img is None or table_img.size == 0:
            return []

        tensor, scale_factor = self.preprocess_image(table_img)
        outputs = self.session.run(None, {self.input_name: tensor}, self.run_options)
        return self.postprocess_outputs(outputs[0], scale_factor, thr=thr)

    @staticmethod
    def construct_markdown(
        table_components: list[dict[str, Any]],
        ocr_boxes: list[dict[str, Any]],
    ) -> str:
        """Construct a Markdown table from detected components and OCR text boxes.

        Args:
            table_components: Detected rows, columns, and headers from TSR.
            ocr_boxes: OCR text boxes inside the table crop with format:
                       {'bbox': [x0, y0, x1, y1], 'text': str}

        Returns:
            Formatted Markdown table string.
        """
        rows = [c for c in table_components if "row" in c["type"] and "header" not in c["type"]]
        columns = [c for c in table_components if "column" in c["type"] and "header" not in c["type"]]

        # Sort rows top-to-bottom, columns left-to-right
        rows.sort(key=lambda r: r["bbox"][1])
        columns.sort(key=lambda c: c["bbox"][0])

        # If no explicit rows or columns detected, fallback to grouping OCR boxes by horizontal lines
        if not rows or not columns:
            if not ocr_boxes:
                return ""
            sorted_ocr = sorted(ocr_boxes, key=lambda b: (b["bbox"][1], b["bbox"][0]))
            line_groups: list[list[dict[str, Any]]] = []
            curr_group: list[dict[str, Any]] = []

            for b in sorted_ocr:
                if not curr_group:
                    curr_group.append(b)
                elif abs(b["bbox"][1] - curr_group[0]["bbox"][1]) < 12:
                    curr_group.append(b)
                else:
                    line_groups.append(sorted(curr_group, key=lambda x: x["bbox"][0]))
                    curr_group = [b]
            if curr_group:
                line_groups.append(sorted(curr_group, key=lambda x: x["bbox"][0]))

            # Build simple markdown
            md_lines = []
            if line_groups:
                header_row = line_groups[0]
                header_cells = [b["text"].strip().replace("|", "\\|") for b in header_row]
                md_lines.append("| " + " | ".join(header_cells) + " |")
                md_lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

                for row in line_groups[1:]:
                    cells = [b["text"].strip().replace("|", "\\|") for b in row]
                    while len(cells) < len(header_cells):
                        cells.append("")
                    md_lines.append("| " + " | ".join(cells[:len(header_cells)]) + " |")
            return "\n".join(md_lines)

        # 2D Grid Cell Mapping
        num_rows = len(rows)
        num_cols = len(columns)
        grid: list[list[list[str]]] = [[[] for _ in range(num_cols)] for _ in range(num_rows)]

        for box in ocr_boxes:
            bx0, by0, bx1, by1 = box["bbox"]
            bcx = (bx0 + bx1) / 2.0
            bcy = (by0 + by1) / 2.0
            text = box["text"].strip().replace("|", "\\|")
            if not text:
                continue

            # Find matching column
            best_c = 0
            best_c_dist = float("inf")
            for c_idx, col in enumerate(columns):
                cx0, _, cx1, _ = col["bbox"]
                if cx0 <= bcx <= cx1:
                    best_c = c_idx
                    break
                dist = min(abs(bcx - cx0), abs(bcx - cx1))
                if dist < best_c_dist:
                    best_c_dist = dist
                    best_c = c_idx

            # Find matching row
            best_r = 0
            best_r_dist = float("inf")
            for r_idx, row in enumerate(rows):
                _, ry0, _, ry1 = row["bbox"]
                if ry0 <= bcy <= ry1:
                    best_r = r_idx
                    break
                dist = min(abs(bcy - ry0), abs(bcy - ry1))
                if dist < best_r_dist:
                    best_r_dist = dist
                    best_r = r_idx

            grid[best_r][best_c].append(text)

        # Render Markdown Table
        md_rows = []
        for r_idx in range(num_rows):
            row_cells = [" ".join(grid[r_idx][c_idx]).strip() for c_idx in range(num_cols)]
            md_rows.append("| " + " | ".join(row_cells) + " |")
            if r_idx == 0:
                md_rows.append("| " + " | ".join(["---"] * num_cols) + " |")

        return "\n".join(md_rows)

    def extract_table(
        self,
        table_img: np.ndarray,
        ocr_boxes: list[dict[str, Any]],
        thr: float = DEFAULT_TSR_THRESHOLD,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Recognize table structure and build Markdown table string.

        Args:
            table_img: BGR image crop of the table.
            ocr_boxes: OCR bounding boxes relative to table image.
            thr: Confidence threshold for TSR components.

        Returns:
            Tuple of (markdown_string, detected_components)
        """
        components = self.recognize_structure(table_img, thr=thr)
        markdown = self.construct_markdown(components, ocr_boxes)
        return markdown, components
