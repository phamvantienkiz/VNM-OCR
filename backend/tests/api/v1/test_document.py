"""Integration tests for Document extraction endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v1_document_extract_image(client: AsyncClient, sample_image_bytes: bytes):
    files = {"file": ("document.png", sample_image_bytes, "image/png")}
    response = await client.post(
        "/api/v1/document/extract?extract_tables=true",
        files=files,
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_pages" in data
    assert data["total_pages"] == 1
    assert "full_markdown" in data
    assert "pages" in data
    assert len(data["pages"]) == 1
    assert data["elapsed_ms"] > 0
