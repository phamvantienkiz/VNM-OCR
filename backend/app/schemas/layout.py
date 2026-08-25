"""Schemas for Document Layout Analysis (DLA)."""

from pydantic import BaseModel, ConfigDict, Field


class LayoutRegionResult(BaseModel):
    """Single detected layout region."""

    type: str = Field(
        ...,
        description="Region type (title, text, figure, figure_caption, table, table_caption, table_footnote, equation, reference)",
    )
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box [x1, y1, x2, y2]",
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

    model_config = ConfigDict(extra="forbid")


class LayoutResponse(BaseModel):
    """Response payload for Document Layout Analysis."""

    regions: list[LayoutRegionResult] = Field(default_factory=list, description="Detected layout regions")
    total_regions: int = Field(..., ge=0, description="Total number of layout regions detected")
    elapsed_ms: float = Field(..., description="Execution duration in milliseconds")

    model_config = ConfigDict(extra="forbid")
