"""Integration tests for Real Administrative PDF document processing via API endpoints."""

from pathlib import Path
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v1_extract_real_administrative_pdf(client: AsyncClient, real_pdf_bytes: bytes):
    """Test full document extraction pipeline on real scanned Vietnamese administrative PDF."""
    files = {"file": ("bao_cao.pdf", real_pdf_bytes, "application/pdf")}
    response = await client.post(
        "/api/v1/document/extract",
        params={"extract_tables": True, "resolution": 150},
        files=files,
    )

    assert response.status_code == 200
    data = response.json()

    # 1. Structural assertions
    assert data["total_pages"] == 1
    assert len(data["pages"]) == 1
    assert data["elapsed_ms"] > 0
    assert isinstance(data["full_markdown"], str)
    assert len(data["full_markdown"]) > 100

    page = data["pages"][0]
    assert page["page_number"] == 1

    # 2. Text line detection assertions
    assert len(page["text_lines"]) >= 30
    for line in page["text_lines"]:
        assert "bbox" in line
        assert len(line["bbox"]) == 4  # polygon with 4 points
        assert "text" in line and len(line["text"]) > 0
        assert 0.0 <= line["score"] <= 1.0

    # 3. Layout Region detection assertions
    assert len(page["layout_regions"]) >= 5
    region_types = {r["type"] for r in page["layout_regions"]}
    # Administrative documents should detect text and title regions
    assert "text" in region_types or "title" in region_types

    # 4. Domain / Vietnamese Content semantic assertions
    markdown_upper = data["full_markdown"].upper()
    assert "UBND" in markdown_upper or "TRẢNG BÀNG" in markdown_upper
    assert "BÁO CÁO" in markdown_upper
    assert "GIÁO DỤC" in markdown_upper or "ĐÀO TẠO" in markdown_upper
