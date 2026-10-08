"""PDF and Multi-page Document Processing Utilities."""

import io
import logging
from typing import Generator, BinaryIO
import numpy as np
import pdfplumber
from PIL import Image

from app.utils.image_utils import (
    decode_image_bytes,
    decode_image_file,
    is_pdf_file,
    pil_to_opencv,
)

logger = logging.getLogger(__name__)

DIGITAL_CHAR_THRESHOLD = 50


def is_pdf(payload: bytes) -> bool:
    """Check if byte payload starts with the PDF magic header."""
    return payload.startswith(b"%PDF")


def _try_extract_digital_text(page: pdfplumber.page.Page) -> str | None:
    """Kiểm tra và trích xuất text điện tử chuẩn chỉ trong 1 lần gọi (tránh lặp tính toán)."""
    try:
        text = page.extract_text() or ""
        if len(text.strip()) >= DIGITAL_CHAR_THRESHOLD:
            return text
    except Exception:
        pass
    return None


def iter_document_pages_smart(
    file_input: BinaryIO | bytes, resolution: int = 150
) -> Generator[tuple[int, np.ndarray | str], None, None]:
    """Generator stream từng trang từ file-like object (SpooledTemporaryFile) hoặc bytes:

    - Đọc trực tiếp từ file_input (không tạo bản sao bytes dư thừa trong RAM).
    - Trả về text string (Fast Path) nếu trang là born-digital.
    - Render và trả về ảnh OpenCV BGR (Slow Path) nếu là ảnh scan.
    """
    if hasattr(file_input, "read"):
        file_input.seek(0)
        file_obj = file_input
        is_pdf_doc = is_pdf_file(file_obj)
        file_obj.seek(0)
    else:
        file_obj = io.BytesIO(file_input)
        is_pdf_doc = file_input.startswith(b"%PDF")
        file_obj.seek(0)

    if is_pdf_doc:
        with pdfplumber.open(file_obj) as pdf:
            if not pdf.pages:
                raise ValueError("PDF document contains no pages")
            for page_idx, page in enumerate(pdf.pages):
                digital_text = _try_extract_digital_text(page)
                if digital_text is not None:
                    # Fast path: text string (không lặp lại extract_text)
                    yield (page_idx + 1, digital_text)
                else:
                    # Slow path: render thành ảnh và convert thẳng sang BGR
                    cv_img = pil_to_opencv(page.to_image(resolution=resolution).original)
                    yield (page_idx + 1, cv_img)
                    del cv_img  # Giải phóng buffer sau khi consumer hoàn tất
    else:
        cv_img = decode_image_file(file_obj)
        yield (1, cv_img)
        del cv_img


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
