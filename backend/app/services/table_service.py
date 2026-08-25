"""Table Structure Recognition Service Layer."""

import time
import logging
from app.engine.table_engine import TableEngine
from app.engine.ocr_engine import OcrEngine
from app.schemas.table import TableComponent, TableMarkdownResponse
from app.utils.image_utils import decode_image_bytes

logger = logging.getLogger(__name__)


class TableService:
    """Service layer orchestrating Table Structure Recognition and Markdown extraction."""

    def __init__(self, table_engine: TableEngine, ocr_engine: OcrEngine) -> None:
        self.table_engine = table_engine
        self.ocr_engine = ocr_engine

    def process_image(self, image_bytes: bytes, threshold: float = 0.2) -> TableMarkdownResponse:
        """Run TSR + OCR on a cropped table image and produce structured Markdown."""
        start_time = time.perf_counter()
        img = decode_image_bytes(image_bytes)

        # 1. Run OCR on table image
        raw_ocr = self.ocr_engine.predict(img)
        formatted_ocr_boxes = []
        for box, (text, score) in raw_ocr:
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            formatted_ocr_boxes.append({
                "bbox": [min(x_coords), min(y_coords), max(x_coords), max(y_coords)],
                "text": text,
                "score": score,
            })

        # 2. Extract Table Structure & Construct Markdown
        markdown_str, raw_components = self.table_engine.extract_table(
            img, formatted_ocr_boxes, thr=threshold
        )

        components: list[TableComponent] = []
        for comp in raw_components:
            components.append(
                TableComponent(
                    type=comp["type"],
                    bbox=comp["bbox"],
                    score=float(comp["score"]),
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return TableMarkdownResponse(
            markdown=markdown_str,
            components=components,
            total_components=len(components),
            elapsed_ms=round(elapsed_ms, 2),
        )
