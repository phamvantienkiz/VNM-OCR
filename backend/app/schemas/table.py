"""Schemas for Table Structure Recognition (TSR)."""

from pydantic import BaseModel, ConfigDict, Field


class TableComponent(BaseModel):
    """Single structural component inside a table (row, column, header, spanning cell)."""

    type: str = Field(..., description="Component type (table row, table column, table header, etc.)")
    bbox: list[float] = Field(..., min_length=4, max_length=4, description="Bounding box [x1, y1, x2, y2]")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

    model_config = ConfigDict(extra="forbid")


class TableMarkdownResponse(BaseModel):
    """Response payload for Table Structure Recognition and Markdown conversion."""

    markdown: str = Field(..., description="Constructed Markdown table format")
    components: list[TableComponent] = Field(default_factory=list, description="Detected structural components")
    total_components: int = Field(..., ge=0, description="Total number of components detected")
    elapsed_ms: float = Field(..., description="Execution duration in milliseconds")

    model_config = ConfigDict(extra="forbid")
