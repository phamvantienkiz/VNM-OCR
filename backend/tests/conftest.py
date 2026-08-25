"""Global Pytest Fixtures."""

from pathlib import Path
from typing import AsyncGenerator
import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP Client fixture for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Fixture providing sample image bytes from img directory."""
    img_dir = Path(__file__).resolve().parents[2] / "img"
    images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No sample images found in img directory")

    with open(images[0], "rb") as f:
        return f.read()
