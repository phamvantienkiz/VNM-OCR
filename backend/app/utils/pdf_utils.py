"""PDF and Multi-page Document Processing Utilities."""

import io
import logging
from typing import BinaryIO
import numpy as np
import pdfplumber
from PIL import Image

from app.utils.image_utils import decode_image_bytes, pil_to_opencv

logger = logging.getLogger(__name__)


def is_pdf(payload: bytes) -> bool:
    """Check if byte payload starts with the PDF magic header."""
    return payload.startswith(b"%PDF")


def render_pdf_to_images(pdf_bytes: bytes, resolution: int = 150) -> list[np.ndarray]:
    """Render pages of a PDF document into a list of OpenCV BGR NumPy arrays.

    Args:
        pdf_bytes: Raw bytes of the PDF document.
        resolution: Rendering DPI (default 150 for balanced speed and OCR accuracy).

    Returns:
        List of OpenCV BGR images (one per page).

    Raises:
        ValueError: If PDF parsing fails or document contains 0 pages.
    """
    if not pdf_bytes:
        raise ValueError("PDF payload is empty")

    images: list[np.ndarray] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                raise ValueError("PDF document contains no pages")

            for page_idx, page in enumerate(pdf.pages):
                logger.debug("Rendering PDF page %d (resolution=%d)", page_idx + 1, resolution)
                page_img: Image.Image = page.to_image(resolution=resolution).original
                cv_img = pil_to_opencv(page_img)
                images.append(cv_img)
    except Exception as e:
        logger.error("Failed to render PDF document: %s", e)
        raise ValueError(f"Failed to render PDF: {e}") from e

    return images


def load_document_images(file_bytes: bytes, resolution: int = 150) -> list[np.ndarray]:
    """Load an uploaded document (PDF or single image) into a list of OpenCV BGR NumPy arrays."""
    if is_pdf(file_bytes):
        return render_pdf_to_images(file_bytes, resolution=resolution)
    else:
        img = decode_image_bytes(file_bytes)
        return [img]
