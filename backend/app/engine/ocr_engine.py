"""ONNX-based Pure OCR Engine.

Combines PP-OCRv5 DBNet Text Detector with VietOCR Autoregressive Recognizer
(CNN + Encoder + Decoder) entirely on ONNX Runtime without PyTorch.
"""

from pathlib import Path
from typing import Any
import copy
import time
import logging
import cv2
import numpy as np

from app.engine.model_loader import load_onnx_session
from app.engine.operators import (
    DetResizeForTest,
    NormalizeImage,
    ToCHWImage,
    KeepKeys,
    transform,
)
from app.engine.postprocess import DBPostProcess
from app.engine.vocab import VietVocab
from app.core.constants import (
    TOKEN_SOS,
    TOKEN_EOS,
    DEFAULT_DROP_SCORE,
    DEFAULT_REC_IMAGE_HEIGHT,
)

logger = logging.getLogger(__name__)


def translate_onnx(
    img_batch: np.ndarray,
    cnn_session: Any,
    encoder_session: Any,
    decoder_session: Any,
    run_options: Any = None,
    max_seq_length: int = 128,
) -> np.ndarray:
    """Run VietOCR autoregressive sequence decoding on ONNX Runtime without PyTorch.

    Args:
        img_batch: Batch of line images (B, C, H, W) normalized in [0.0, 1.0].
        cnn_session: ONNX InferenceSession for cnn.onnx.
        encoder_session: ONNX InferenceSession for encoder.onnx.
        decoder_session: ONNX InferenceSession for decoder.onnx.
        run_options: ONNX RunOptions with memory shrinkage.
        max_seq_length: Maximum sequence length limit.

    Returns:
        Array of shape (B, seq_length) containing token IDs.
    """
    batch_size = img_batch.shape[0]

    # 1. Feature Extraction (CNN)
    cnn_input_name = cnn_session.get_inputs()[0].name
    cnn_output = cnn_session.run(None, {cnn_input_name: img_batch}, run_options)
    src = cnn_output[0]

    # 2. Sequence Encoding (Encoder)
    encoder_input_name = encoder_session.get_inputs()[0].name
    encoder_outputs, hidden = encoder_session.run(None, {encoder_input_name: src}, run_options)

    # 3. Autoregressive Decoding (Decoder)
    translated_tokens = [[TOKEN_SOS] * batch_size]
    max_length = 0

    dec_inp_tgt = decoder_session.get_inputs()[0].name
    dec_inp_hidden = decoder_session.get_inputs()[1].name
    dec_inp_encoder = decoder_session.get_inputs()[2].name

    while max_length <= max_seq_length:
        current_trans = np.asarray(translated_tokens).T
        if np.all(np.any(current_trans == TOKEN_EOS, axis=1)):
            break

        last_tokens = translated_tokens[-1]
        decoder_feed = {
            dec_inp_tgt: np.array(last_tokens, dtype=np.int64),
            dec_inp_hidden: hidden,
            dec_inp_encoder: encoder_outputs,
        }

        output, hidden, _ = decoder_session.run(None, decoder_feed, run_options)

        # Output shape: (B, vocab_size) -> take argmax over vocabulary
        next_indices = np.argmax(output, axis=-1).tolist()
        translated_tokens.append(next_indices)
        max_length += 1

    return np.asarray(translated_tokens).T


class TextDetector:
    """DBNet Text Detector using det.onnx."""

    def __init__(
        self,
        model_path: str | Path,
        device: str = "auto",
        device_id: int = 0,
    ) -> None:
        self.session, self.run_options = load_onnx_session(model_path, device, device_id)
        self.input_tensor = self.session.get_inputs()[0]

        img_h, img_w = self.input_tensor.shape[2:]
        if isinstance(img_h, int) and isinstance(img_w, int) and img_h > 0 and img_w > 0:
            resize_op = DetResizeForTest(image_shape=[img_h, img_w])
        else:
            resize_op = DetResizeForTest(limit_side_len=960, limit_type="max")

        self.preprocess_ops = [
            resize_op,
            NormalizeImage(),
            ToCHWImage(),
            KeepKeys(keep_keys=["image", "shape"]),
        ]
        self.postprocess_op = DBPostProcess(thresh=0.3, box_thresh=0.5, unclip_ratio=1.5)

    @staticmethod
    def order_points_clockwise(pts: np.ndarray) -> np.ndarray:
        """Order quadrilateral polygon points clockwise starting from top-left."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        tmp = np.delete(pts, (np.argmin(s), np.argmax(s)), axis=0)
        diff = np.diff(np.array(tmp), axis=1)
        rect[1] = tmp[np.argmin(diff)]
        rect[3] = tmp[np.argmax(diff)]
        return rect

    @staticmethod
    def clip_det_res(points: np.ndarray, img_height: int, img_width: int) -> np.ndarray:
        """Clip polygon points to stay within image boundaries."""
        for pno in range(points.shape[0]):
            points[pno, 0] = int(min(max(points[pno, 0], 0), img_width - 1))
            points[pno, 1] = int(min(max(points[pno, 1], 0), img_height - 1))
        return points

    def filter_tag_det_res(self, dt_boxes: list[np.ndarray], image_shape: tuple[int, int]) -> list[np.ndarray]:
        """Filter out degenerate and tiny bounding boxes (<= 3px)."""
        img_height, img_width = image_shape[0:2]
        dt_boxes_new = []
        for box in dt_boxes:
            if isinstance(box, list):
                box = np.array(box)
            box = self.order_points_clockwise(box)
            box = self.clip_det_res(box, img_height, img_width)
            rect_width = int(np.linalg.norm(box[0] - box[1]))
            rect_height = int(np.linalg.norm(box[0] - box[3]))
            if rect_width <= 3 or rect_height <= 3:
                continue
            dt_boxes_new.append(box)
        return dt_boxes_new

    def __call__(self, img: np.ndarray) -> tuple[list[np.ndarray], float]:
        """Run text detection on a single image.

        Args:
            img: BGR image as NumPy array.

        Returns:
            Tuple of (detected_boxes_list, elapsed_time_seconds)
        """
        ori_shape = img.shape
        start_time = time.time()

        data = {"image": img}
        data_res = transform(data, self.preprocess_ops)
        if data_res is None:
            return [], 0.0

        proc_img, shape_list = data_res
        proc_img = np.expand_dims(proc_img, axis=0).astype(np.float32)
        shape_list = np.expand_dims(shape_list, axis=0)

        outputs = self.session.run(None, {self.input_tensor.name: proc_img}, self.run_options)
        post_result = self.postprocess_op({"maps": outputs[0]}, shape_list)

        raw_boxes = post_result[0]["points"]
        filtered_boxes = self.filter_tag_det_res(raw_boxes, ori_shape)

        elapsed = time.time() - start_time
        return filtered_boxes, elapsed


class TextRecognizer:
    """VietOCR Text Recognizer using cnn.onnx, encoder.onnx, and decoder.onnx."""

    def __init__(
        self,
        models_dir: str | Path,
        device: str = "auto",
        device_id: int = 0,
        vocab: VietVocab | None = None,
    ) -> None:
        models_path = Path(models_dir)
        self.vocab = vocab or VietVocab()

        self.cnn_session, self.cnn_run_options = load_onnx_session(
            models_path / "cnn.onnx", device, device_id
        )
        self.encoder_session, self.encoder_run_options = load_onnx_session(
            models_path / "encoder.onnx", device, device_id
        )
        self.decoder_session, self.decoder_run_options = load_onnx_session(
            models_path / "decoder.onnx", device, device_id
        )

    def preprocess_line_image(self, img: np.ndarray, target_height: int = DEFAULT_REC_IMAGE_HEIGHT) -> np.ndarray:
        """Resize cropped text line image to fixed height and normalize to CHW."""
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        h, w = img.shape[:2]
        new_w = max(int(w * (target_height / float(h))), 32)
        resized = cv2.resize(img, (new_w, target_height), interpolation=cv2.INTER_LINEAR)

        # Transpose to CHW and normalize to [0, 1]
        chw = resized.transpose(2, 0, 1).astype(np.float32) / 255.0
        return chw

    def __call__(
        self,
        img_list: list[np.ndarray],
        batch_size: int = 16,
    ) -> tuple[list[tuple[str, float]], float]:
        """Recognize text on a list of cropped line images in batches.

        Args:
            img_list: List of line images as NumPy arrays.
            batch_size: Batch inference size.

        Returns:
            Tuple of (list of (text, confidence), elapsed_time_seconds)
        """
        if not img_list:
            return [], 0.0

        start_time = time.time()
        results: list[tuple[str, float]] = []

        # Process each image individually or in width-grouped batches
        for img in img_list:
            if img is None or img.size == 0 or img.shape[0] < 2 or img.shape[1] < 2:
                results.append(("", 0.0))
                continue

            chw_img = self.preprocess_line_image(img)
            batch_tensor = np.expand_dims(chw_img, axis=0)

            token_ids_batch = translate_onnx(
                batch_tensor,
                self.cnn_session,
                self.encoder_session,
                self.decoder_session,
                self.decoder_run_options,
            )

            decoded_text = self.vocab.decode(token_ids_batch[0])
            results.append((decoded_text, 1.0))

        elapsed = time.time() - start_time
        return results, elapsed


class OcrEngine:
    """Complete OCR Orchestrator integrating Detection and Recognition."""

    def __init__(
        self,
        models_dir: str | Path,
        device: str = "auto",
        device_id: int = 0,
        drop_score: float = DEFAULT_DROP_SCORE,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.drop_score = drop_score

        self.detector = TextDetector(self.models_dir / "det.onnx", device, device_id)
        self.recognizer = TextRecognizer(self.models_dir, device, device_id)

    @staticmethod
    def get_rotate_crop_image(img: np.ndarray, points: np.ndarray) -> np.ndarray:
        """Crop and perspective-align quadrilateral text region."""
        assert len(points) == 4, "shape of points must be 4*2"
        crop_w = int(
            max(
                np.linalg.norm(points[0] - points[1]),
                np.linalg.norm(points[2] - points[3]),
            )
        )
        crop_h = int(
            max(
                np.linalg.norm(points[0] - points[3]),
                np.linalg.norm(points[1] - points[2]),
            )
        )
        crop_w = max(crop_w, 4)
        crop_h = max(crop_h, 4)

        pts_std = np.float32([[0, 0], [crop_w, 0], [crop_w, crop_h], [0, crop_h]])
        m = cv2.getPerspectiveTransform(points.astype(np.float32), pts_std)
        dst_img = cv2.warpPerspective(
            img,
            m,
            (crop_w, crop_h),
            borderMode=cv2.BORDER_REPLICATE,
            flags=cv2.INTER_CUBIC,
        )

        # Rotate 90 degrees if vertical text
        if dst_img.shape[0] * 1.0 / dst_img.shape[1] >= 1.5:
            dst_img = np.rot90(dst_img)
        return dst_img

    @staticmethod
    def sorted_boxes(dt_boxes: list[np.ndarray]) -> list[np.ndarray]:
        """Sort detected text boxes from top-to-bottom and left-to-right on the same line."""
        if not dt_boxes:
            return []

        sorted_bxs = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
        boxes = list(sorted_bxs)

        num_boxes = len(boxes)
        for i in range(num_boxes - 1):
            for j in range(i, -1, -1):
                if (
                    abs(boxes[j + 1][0][1] - boxes[j][0][1]) < 10
                    and (boxes[j + 1][0][0] < boxes[j][0][0])
                ):
                    boxes[j], boxes[j + 1] = boxes[j + 1], boxes[j]
                else:
                    break
        return boxes

    def detect(self, img: np.ndarray) -> list[np.ndarray]:
        """Run only text detection."""
        dt_boxes, _ = self.detector(img)
        return self.sorted_boxes(dt_boxes)

    def recognize_crops(self, crop_images: list[np.ndarray]) -> list[tuple[str, float]]:
        """Run recognition on pre-cropped text images."""
        rec_res, _ = self.recognizer(crop_images)
        return rec_res

    def predict(
        self, img: np.ndarray
    ) -> list[tuple[list[list[int]], tuple[str, float]]]:
        """Run full OCR pipeline on an image.

        Args:
            img: BGR image as NumPy array.

        Returns:
            List of tuple: (box_4_points, (text, confidence))
        """
        if img is None or img.size == 0:
            return []

        ori_im = img.copy()
        dt_boxes, _ = self.detector(ori_im)
        if not dt_boxes:
            return []

        sorted_dt_boxes = self.sorted_boxes(dt_boxes)
        img_crop_list = []
        for box in sorted_dt_boxes:
            crop = self.get_rotate_crop_image(ori_im, box)
            img_crop_list.append(crop)

        rec_res, _ = self.recognizer(img_crop_list)

        results = []
        for box, (text, score) in zip(sorted_dt_boxes, rec_res):
            if score >= self.drop_score and text.strip():
                results.append((box.tolist(), (text, score)))

        return results

    def __call__(
        self, img: np.ndarray
    ) -> list[tuple[list[list[int]], tuple[str, float]]]:
        """Callable interface matching legacy OCR class."""
        return self.predict(img)
