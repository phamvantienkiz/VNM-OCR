"""Table Structure Recognition Engine (TSR) using YOLOv10 ONNX.

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
    """Table Structure Recognition and Markdown Table Builder."""

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
            self.target_shape = (1024, 1024)
        else:
            self.target_shape = (int(self.input_shape[0]), int(self.input_shape[1]))

        self.labels = labels or TSR_LABELS

    def preprocess_image(self, img: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """Preprocess cropped table image with letterbox resize, border padding, and CHW normalization."""
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
        """Filter YOLOv10 TSR outputs, scale back to table image dimensions, and apply NMS."""
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
            label_name = self.labels[cid] if cid < len(self.labels) else "table row"
            results.append({
                "type": label_name.lower(),
                "bbox": [float(c) for c in coords[i].tolist()],
                "score": float(scores[i]),
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
        headers = [c for c in table_components if "header" in c["type"]]

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
                    # Pad cells to match header length if needed
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
