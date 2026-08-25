"""Table Structure Recognition Endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from app.api.deps import get_table_service
from app.services.table_service import TableService
from app.schemas.table import TableMarkdownResponse

router = APIRouter()


@router.post(
    "/table",
    response_model=TableMarkdownResponse,
    summary="Extract table structure to Markdown",
    description="Analyzes table rows, columns, and text to construct a clean Markdown table representation.",
)
async def recognize_table(
    file: UploadFile = File(..., description="Cropped table image file"),
    threshold: float = Query(default=0.2, ge=0.0, le=1.0, description="TSR detection threshold"),
    service: TableService = Depends(get_table_service),
) -> TableMarkdownResponse:
    """Run Table Structure Recognition on an uploaded table image crop."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    return service.process_image(content, threshold=threshold)
