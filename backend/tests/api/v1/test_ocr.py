"""Integration tests for OCR endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v1_ocr_endpoint(client: AsyncClient, sample_image_bytes: bytes):
    files = {"file": ("test_image.png", sample_image_bytes, "image/png")}
    response = await client.post("/api/v1/ocr", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "lines" in data
    assert "total_lines" in data
    assert "elapsed_ms" in data
    assert data["elapsed_ms"] > 0


@pytest.mark.asyncio
async def test_legacy_ocr_endpoint(client: AsyncClient, sample_image_bytes: bytes):
    files = {"file": ("test_image.png", sample_image_bytes, "image/png")}
    response = await client.post("/api/ocr", files=files)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_ocr_endpoint_empty_file(client: AsyncClient):
    files = {"file": ("empty.png", b"", "image/png")}
    response = await client.post("/api/v1/ocr", files=files)
    assert response.status_code == 400
