"""Unit tests for Pydantic Schemas."""

import pytest
from pydantic import ValidationError
from app.schemas.common import Point2D, BaseResponse
from app.schemas.ocr import OCRLineResult, OCRResponse
from app.schemas.layout import LayoutRegionResult, LayoutResponse
from app.schemas.table import TableComponent, TableMarkdownResponse
from app.schemas.document import DocumentPageResult, DocumentExtractionResponse


def test_ocr_response_schema():
    line = OCRLineResult(
        bbox=[[0, 0], [100, 0], [100, 30], [0, 30]],
        text="Cộng hòa Xã hội Chủ nghĩa Việt Nam",
        score=0.98,
    )
    resp = OCRResponse(lines=[line], total_lines=1, elapsed_ms=123.4)
    assert resp.total_lines == 1
    assert resp.lines[0].text == "Cộng hòa Xã hội Chủ nghĩa Việt Nam"


def test_layout_response_schema():
    region = LayoutRegionResult(
        type="title",
        bbox=[10.0, 20.0, 300.0, 80.0],
        score=0.95,
    )
    resp = LayoutResponse(regions=[region], total_regions=1, elapsed_ms=45.6)
    assert resp.total_regions == 1
    assert resp.regions[0].type == "title"


def test_table_response_schema():
    comp = TableComponent(
        type="table row",
        bbox=[0.0, 10.0, 200.0, 40.0],
        score=0.89,
    )
    resp = TableMarkdownResponse(
        markdown="| Cột 1 | Cột 2 |\n|---|---|\n| A | B |",
        components=[comp],
        total_components=1,
        elapsed_ms=50.0,
    )
    assert "| Cột 1 |" in resp.markdown
    assert resp.total_components == 1


def test_document_response_schema():
    page = DocumentPageResult(
        page_number=1,
        text_lines=[],
        layout_regions=[],
        tables_markdown=["| A | B |"],
        page_markdown="# Tiêu đề\n\nNội dung trang 1",
    )
    doc_resp = DocumentExtractionResponse(
        total_pages=1,
        full_markdown="# Tiêu đề\n\nNội dung trang 1",
        pages=[page],
        elapsed_ms=250.0,
    )
    assert doc_resp.total_pages == 1
    assert "# Tiêu đề" in doc_resp.full_markdown


def test_schema_validation_error():
    # Negative score should fail validation (ge=0.0)
    with pytest.raises(ValidationError):
        OCRLineResult(
            bbox=[[0, 0], [10, 0], [10, 10], [0, 10]],
            text="Test",
            score=-0.5,
        )

    # Score > 1.0 should fail validation (le=1.0)
    with pytest.raises(ValidationError):
        LayoutRegionResult(
            type="text",
            bbox=[0, 0, 10, 10],
            score=1.5,
        )
