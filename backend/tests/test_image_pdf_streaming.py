"""Unit tests for image_utils and pdf_utils streaming optimizations."""

import io
from PIL import Image
import numpy as np
from app.utils.image_utils import (
    pil_to_opencv,
    opencv_to_pil,
    is_pdf_file,
    decode_image_file,
)
from app.utils.pdf_utils import iter_document_pages_smart


def test_pil_to_opencv_zero_copy():
    pil_img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    cv_img = pil_to_opencv(pil_img)
    assert cv_img.shape == (64, 64, 3)
    # Red in RGB is (255, 0, 0), in BGR is (0, 0, 255)
    assert cv_img[0, 0, 0] == 0  # Blue
    assert cv_img[0, 0, 2] == 255  # Red

    # Round trip
    pil_back = opencv_to_pil(cv_img)
    assert pil_back.size == (64, 64)


def test_decode_image_file():
    pil_img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    assert not is_pdf_file(buf)
    buf.seek(0)
    img_arr = decode_image_file(buf)
    assert img_arr.shape == (32, 32, 3)


def test_iter_document_pages_smart_image():
    pil_img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    pages = list(iter_document_pages_smart(buf))
    assert len(pages) == 1
    page_num, data = pages[0]
    assert page_num == 1
    assert isinstance(data, np.ndarray)
    assert data.shape == (32, 32, 3)
