"""Common Schemas and Base Response Models."""

from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Point2D(BaseModel):
    """2D Point coordinate."""

    x: float
    y: float

    model_config = ConfigDict(extra="forbid")


class BaseResponse(BaseModel, Generic[T]):
    """Standard API Base Response wrapper."""

    success: bool = True
    message: str | None = None
    data: T | None = None
    elapsed_ms: float | None = Field(default=None, description="Execution time in milliseconds")

    model_config = ConfigDict(extra="forbid")
