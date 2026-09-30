"""Document Extraction Service Layer for RAG and Chatbot Document Ingestion.

Implements the 7-step unified extraction pipeline:
  1. PDF / Image rendering into page images.
  2. Document Layout Analysis (DLA).
  3. Text Detection & Recognition (OCR).
  4. Layout & Text Fusion with garbage filtering and reading order sort.
  5. Table Structure Recognition (TSR) to Markdown.
  6. Block-level merging into clean Page Markdown.
  7. Multi-page document aggregation into Full Markdown.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any
import time
import logging
import re
import cv2
import numpy as np

from app.engine.manager import EngineManager
from app.schemas.ocr import OCRLineResult
from app.schemas.layout import LayoutRegionResult
from app.schemas.document import DocumentPageResult, DocumentExtractionResponse
from app.utils.pdf_utils import load_document_images

logger = logging.getLogger(__name__)


class DocumentService:
    """Orchestrates end-to-end multi-page document extraction for RAG pipelines."""

    def __init__(self, engine_manager: EngineManager) -> None:
        self.engine_manager = engine_manager
        self.ocr_engine = engine_manager.ocr_engine
        self.layout_engine = engine_manager.layout_engine
        self.table_engine = engine_manager.table_engine

    def extract_document(
        self,
        file_bytes: bytes,
        extract_tables: bool = True,
        resolution: int = 150,
    ) -> DocumentExtractionResponse:
        """Extract multi-page PDF or image document into structured Markdown for RAG ingestion.

        Args:
            file_bytes: Raw bytes of uploaded PDF or image file.
            extract_tables: If True, executes TSR on table crops to build Markdown tables.
            resolution: Rendering DPI if input is PDF.

        Returns:
            DocumentExtractionResponse with unified full_markdown and structured page breakdown.
        """
        start_time = time.perf_counter()

        # Step 1: Render Document Pages
        page_images = load_document_images(file_bytes, resolution=resolution)
        total_pages = len(page_images)
        logger.info("Processing document with %d page(s)...", total_pages)

        pages_result: list[DocumentPageResult] = []
        page_markdowns: list[str] = []

        for page_idx, page_img in enumerate(page_images, start=1):
            page_h, page_w = page_img.shape[:2]

            # Step 2 & 3: Run OCR on Page
            raw_ocr = self.ocr_engine.predict(page_img)
            ocr_boxes: list[dict[str, Any]] = []
            text_lines_schema: list[OCRLineResult] = []

            for box, (text, score) in raw_ocr:
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                bbox_4 = [min(xs), min(ys), max(xs), max(ys)]
                ocr_boxes.append({
                    "points": box,
                    "bbox": bbox_4,
                    "text": text,
                    "score": float(score),
                    "page_number": page_idx,
                })
                text_lines_schema.append(
                    OCRLineResult(bbox=box, text=text, score=float(score))
                )

            # Step 4: Run DLA and Fuse with OCR
            fused_boxes, raw_page_layouts = self.layout_engine.fuse_with_ocr(
                [page_img], [ocr_boxes], thr=0.4, drop_garbage=True
            )
            raw_layouts = raw_page_layouts[0] if raw_page_layouts else []

            layout_regions_schema: list[LayoutRegionResult] = [
                LayoutRegionResult(
                    type=r["type"],
                    bbox=r["bbox"],
                    score=float(r["score"]),
                )
                for r in raw_layouts
            ]

            # Step 5 & 6: Process Regions and Assemble Page Markdown
            tables_markdown: list[str] = []
            page_blocks: list[dict[str, Any]] = []

            # Separate table regions
            table_regions = [r for r in raw_layouts if r["type"] == "table"]
            processed_table_boxes: set[int] = set()

            if extract_tables and table_regions:
                for t_idx, t_reg in enumerate(table_regions):
                    tx0, ty0, tx1, ty1 = [int(v) for v in t_reg["bbox"]]
                    tx0, ty0 = max(0, tx0), max(0, ty0)
                    tx1, ty1 = min(page_w, tx1), min(page_h, ty1)

                    if (tx1 - tx0) < 10 or (ty1 - ty0) < 10:
                        continue

                    # Crop table image
                    table_crop = page_img[ty0:ty1, tx0:tx1]

                    # Filter OCR boxes within this table
                    tbl_ocr = []
                    for b_i, b in enumerate(fused_boxes):
                        bx0, by0, bx1, by1 = b["bbox"]
                        if (
                            bx0 >= tx0 - 5
                            and bx1 <= tx1 + 5
                            and by0 >= ty0 - 5
                            and by1 <= ty1 + 5
                        ):
                            processed_table_boxes.add(b_i)
                            tbl_ocr.append({
                                "bbox": [bx0 - tx0, by0 - ty0, bx1 - tx0, by1 - ty0],
                                "text": b["text"],
                                "score": b["score"],
                            })

                    # Run TSR and build markdown table
                    md_table, _ = self.table_engine.extract_table(table_crop, tbl_ocr)
                    if md_table.strip():
                        tables_markdown.append(md_table)
                        page_blocks.append({
                            "top": ty0,
                            "type": "table",
                            "content": md_table,
                        })

            # Process non-table OCR text lines
            non_table_boxes = [
                b for b_i, b in enumerate(fused_boxes) if b_i not in processed_table_boxes
            ]
            # Sort reading order: Top-to-bottom, Left-to-right
            non_table_boxes.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

            # Group lines into paragraphs / headings based on layout_type and vertical gap
            curr_type: str | None = None
            curr_lines: list[str] = []
            curr_top: float = 0.0

            for b in non_table_boxes:
                b_type = b.get("layout_type", "text")
                b_text = b["text"].strip()
                if not b_text:
                    continue

                b_top = b["bbox"][1]

                if curr_type is None:
                    curr_type = b_type
                    curr_lines = [b_text]
                    curr_top = b_top
                elif b_type == curr_type and abs(b_top - curr_top) < 35:
                    curr_lines.append(b_text)
                else:
                    # Flush previous group
                    block_content = " ".join(curr_lines)
                    if curr_type == "title":
                        block_content = f"## {block_content}"
                    elif curr_type == "figure_caption":
                        block_content = f"*{block_content}*"
                    elif curr_type == "equation":
                        block_content = f"$$\n{block_content}\n$$"

                    page_blocks.append({
                        "top": curr_top,
                        "type": curr_type,
                        "content": block_content,
                    })

                    curr_type = b_type
                    curr_lines = [b_text]
                    curr_top = b_top

            if curr_lines:
                block_content = " ".join(curr_lines)
                if curr_type == "title":
                    block_content = f"## {block_content}"
                elif curr_type == "figure_caption":
                    block_content = f"*{block_content}*"
                elif curr_type == "equation":
                    block_content = f"$$\n{block_content}\n$$"

                page_blocks.append({
                    "top": curr_top,
                    "type": curr_type,
                    "content": block_content,
                })

            # Sort all blocks on this page by vertical coordinate
            page_blocks.sort(key=lambda x: x["top"])
            page_md = "\n\n".join([blk["content"] for blk in page_blocks if blk["content"].strip()])

            pages_result.append(
                DocumentPageResult(
                    page_number=page_idx,
                    text_lines=text_lines_schema,
                    layout_regions=layout_regions_schema,
                    tables_markdown=tables_markdown,
                    page_markdown=page_md,
                )
            )
            page_markdowns.append(page_md)

        # Step 7: Aggregate Full Markdown
        full_markdown = "\n\n---\n\n".join([pm for pm in page_markdowns if pm.strip()])
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        logger.info(
            "Document extraction completed: %d page(s), %.2f ms",
            total_pages,
            elapsed_ms,
        )

        return DocumentExtractionResponse(
            total_pages=total_pages,
            full_markdown=full_markdown,
            pages=pages_result,
            elapsed_ms=round(elapsed_ms, 2),
        )
