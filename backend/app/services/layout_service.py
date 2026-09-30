"""Document Layout Analysis Service Layer."""

import time
import logging
from app.engine.layout_engine import LayoutEngine
from app.schemas.layout import LayoutRegionResult, LayoutResponse
from app.utils.image_utils import decode_image_bytes

logger = logging.getLogger(__name__)


class LayoutService:
    """Service layer orchestrating Document Layout Analysis operations."""

    def __init__(self, layout_engine: LayoutEngine) -> None:
        self.engine = layout_engine

    def process_image(self, image_bytes: bytes, threshold: float = 0.5) -> LayoutResponse:
        """Run Document Layout Analysis on image bytes."""
        start_time = time.perf_counter()
        img = decode_image_bytes(image_bytes)

        batch_regions = self.engine.forward([img], thr=threshold)
        raw_regions = batch_regions[0] if batch_regions else []

        regions: list[LayoutRegionResult] = []
        for reg in raw_regions:
            regions.append(
                LayoutRegionResult(
                    type=reg["type"],
                    bbox=reg["bbox"],
                    score=float(reg["score"]),
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return LayoutResponse(
            regions=regions,
            total_regions=len(regions),
            elapsed_ms=round(elapsed_ms, 2),
        )
