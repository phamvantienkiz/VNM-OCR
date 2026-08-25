"""Integration tests for Layout endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v1_layout_endpoint(client: AsyncClient, sample_image_bytes: bytes):
    files = {"file": ("test_image.png", sample_image_bytes, "image/png")}
    response = await client.post("/api/v1/layout?threshold=0.3", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert "total_regions" in data
    assert data["elapsed_ms"] > 0
