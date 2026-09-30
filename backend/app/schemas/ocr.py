"""Schemas for OCR Endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class OCRLineResult(BaseModel):
    """Single detected and recognized text line."""

    bbox: list[list[int]] = Field(
        ...,
        description="4-point polygon coordinates [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]",
    )
    text: str = Field(..., description="Recognized Unicode UTF-8 Vietnamese text")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

    model_config = ConfigDict(extra="forbid")


class OCRResponse(BaseModel):
    """Response payload for image OCR."""

    lines: list[OCRLineResult] = Field(default_factory=list, description="List of recognized text lines")
    total_lines: int = Field(..., ge=0, description="Total number of text lines detected")
    elapsed_ms: float = Field(..., description="Execution duration in milliseconds")

    model_config = ConfigDict(extra="forbid")
