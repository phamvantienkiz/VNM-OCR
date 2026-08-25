"""Image Utility Functions."""

import io
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


def pil_to_opencv(pil_img: Image.Image) -> np.ndarray:
    """Convert a PIL Image instance to an OpenCV BGR NumPy array."""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    rgb_arr = np.array(pil_img)
    bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
    return bgr_arr


def opencv_to_pil(cv_img: np.ndarray) -> Image.Image:
    """Convert an OpenCV BGR NumPy array to a PIL Image instance."""
    rgb_arr = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_arr)
