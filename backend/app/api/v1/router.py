"""API v1 Main Router."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, ocr, layout, table, document, extract

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ocr.router, tags=["OCR"])
api_router.include_router(layout.router, tags=["Layout"])
api_router.include_router(table.router, tags=["Table"])
api_router.include_router(document.router, tags=["Document"])
api_router.include_router(extract.router, tags=["Extract"])
