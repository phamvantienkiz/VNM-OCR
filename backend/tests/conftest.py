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


@pytest.fixture
def real_pdf_path() -> Path:
    """Fixture providing Path to the real scanned administrative PDF sample."""
    pdf_dir = Path(__file__).resolve().parent / "real_pdf_file"
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No sample PDF files found in backend/tests/real_pdf_file")
    return pdf_files[0]


@pytest.fixture
def real_pdf_bytes(real_pdf_path: Path) -> bytes:
    """Fixture providing raw bytes of real scanned administrative PDF sample."""
    return real_pdf_path.read_bytes()

