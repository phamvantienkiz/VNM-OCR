"""Integration tests for Table endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v1_table_endpoint(client: AsyncClient, sample_image_bytes: bytes):
    files = {"file": ("test_table.png", sample_image_bytes, "image/png")}
    response = await client.post("/api/v1/table?threshold=0.2", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "markdown" in data
    assert "components" in data
    assert "total_components" in data
    assert data["elapsed_ms"] > 0
