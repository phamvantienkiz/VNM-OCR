"""Image Utility Functions."""

import io
from typing import BinaryIO
import cv2
import numpy as np
from PIL import Image


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes into a BGR OpenCV NumPy array safely.

    Handles Unicode file paths and corrupted payloads gracefully.

    Raises:
        ValueError: If image decoding fails or payload is empty.
    """
    if not image_bytes:
        raise ValueError("Image data is empty")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image from provided byte stream")
    return img


def decode_image_file(file_obj: BinaryIO) -> np.ndarray:
    """Giải mã ảnh trực tiếp từ file-like object không qua bộ đệm bytes dư thừa."""
    file_obj.seek(0)
    data = file_obj.read()
    file_obj.seek(0)
    if not data:
        raise ValueError("Image data is empty")
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không thể giải mã file ảnh.")
    return img


def is_pdf_file(file_obj: BinaryIO) -> bool:
    """Kiểm tra header PDF trực tiếp từ file-like object."""
    file_obj.seek(0)
    magic = file_obj.read(4)
    file_obj.seek(0)
    return magic == b"%PDF"


def pil_to_opencv(pil_img: Image.Image) -> np.ndarray:
    """Chuyển đổi PIL Image sang mảng OpenCV BGR với tối thiểu bản sao trung gian (zero-copy slice)."""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    # np.array tạo RGB uint8, slice [:, :, ::-1] đảo channel sang BGR tại chỗ (zero-copy view)
    return np.array(pil_img, dtype=np.uint8)[:, :, ::-1]


def opencv_to_pil(cv_img: np.ndarray) -> Image.Image:
    """Convert an OpenCV BGR NumPy array to a PIL Image instance."""
    rgb_arr = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_arr)
