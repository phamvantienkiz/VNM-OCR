"""Engine Lifecycle and Singleton Manager.

Provides centralized access to OCR, Layout, and Table engines with
fail-fast model validation, warmup capabilities, thread-safe lazy-loading,
and explicit session clearing.
"""

from pathlib import Path
import logging
import threading
import numpy as np

from app.core.constants import REQUIRED_MODEL_FILES, DEFAULT_DROP_SCORE
from app.engine.ocr_engine import OcrEngine
from app.engine.layout_engine import LayoutEngine
from app.engine.table_engine import TableEngine
from app.utils.memory_utils import force_garbage_collection_and_trim

logger = logging.getLogger(__name__)


class EngineManager:
    """Singleton Engine Manager coordinating OCR, Layout, and Table inference engines

    with thread-safe on-demand (lazy) instantiation.
    """

    _instance: "EngineManager | None" = None
    _cls_lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "EngineManager":
        with cls._cls_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        models_dir: str | Path | None = None,
        device: str = "auto",
        device_id: int = 0,
        drop_score: float = DEFAULT_DROP_SCORE,
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.Lock()
        self.models_dir = Path(models_dir) if models_dir else Path("models")
        self.device = device
        self.device_id = device_id
        self.drop_score = drop_score

        self._ocr_engine: OcrEngine | None = None
        self._layout_engine: LayoutEngine | None = None
        self._table_engine: TableEngine | None = None
        self._is_ready: bool = False
        self._initialized = True

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the singleton instance and clear all model sessions."""
        with cls._cls_lock:
            if cls._instance is not None:
                cls._instance.clear_sessions()
                cls._instance = None

    def clear_sessions(self) -> None:
        """Clear all active engine sessions and force memory trim."""
        with self._lock:
            logger.info("Clearing all engine sessions...")
            self._ocr_engine = None
            self._layout_engine = None
            self._table_engine = None
            self._is_ready = False
            force_garbage_collection_and_trim()
            logger.info("All engine sessions cleared and memory reclaimed.")

    @staticmethod
    def check_models_exist(models_dir: str | Path) -> list[str]:
        """Check if all required ONNX model files are present.

        Returns:
            List of missing model filenames (empty if all exist).
        """
        dir_path = Path(models_dir)
        missing = []
        for filename in REQUIRED_MODEL_FILES:
            if not (dir_path / filename).is_file():
                missing.append(filename)
        return missing

    def _init_ocr(self) -> None:
        """Initialize OCR engine on demand."""
        ocr_models = ["det.onnx", "cnn.onnx", "encoder.onnx", "decoder.onnx"]
        missing = [m for m in ocr_models if not (self.models_dir / m).is_file()]
        if missing:
            raise FileNotFoundError(f"Missing OCR model file(s) in '{self.models_dir}': {missing}")
        logger.info("On-demand initializing OCR Engine from: %s", self.models_dir)
        self._ocr_engine = OcrEngine(
            models_dir=self.models_dir,
            device=self.device,
            device_id=self.device_id,
            drop_score=self.drop_score,
        )

    def _init_layout(self) -> None:
        """Initialize Layout engine on demand."""
        layout_model = self.models_dir / "layout.onnx"
        if not layout_model.is_file():
            raise FileNotFoundError(f"Missing Layout model file: {layout_model}")
        logger.info("On-demand initializing Layout Engine from: %s", self.models_dir)
        self._layout_engine = LayoutEngine(
            model_path=layout_model,
            device=self.device,
            device_id=self.device_id,
        )

    def _init_table(self) -> None:
        """Initialize Table engine on demand."""
        table_model = self.models_dir / "tsr.onnx"
        if not table_model.is_file():
            raise FileNotFoundError(f"Missing Table model file: {table_model}")
        logger.info("On-demand initializing Table Engine from: %s", self.models_dir)
        self._table_engine = TableEngine(
            model_path=table_model,
            device=self.device,
            device_id=self.device_id,
        )

    def initialize(self) -> None:
        """Verify models directory and instantiate all engines fail-fast."""
        missing = self.check_models_exist(self.models_dir)
        if missing:
            raise FileNotFoundError(
                f"Missing {len(missing)} required ONNX model file(s) in '{self.models_dir}': {missing}"
            )

        with self._lock:
            if self._ocr_engine is None:
                self._init_ocr()
            if self._layout_engine is None:
                self._init_layout()
            if self._table_engine is None:
                self._init_table()
            self._is_ready = True
        logger.info("All OCR and Document engines initialized successfully.")

    def warmup(self) -> None:
        """Warm up engine sessions by executing a dummy pass on synthetic images."""
        if not self._is_ready:
            self.initialize()

        logger.info("Warming up inference engines with dummy passes...")

        # 1. Warmup OCR
        dummy_line = np.ones((32, 128, 3), dtype=np.uint8) * 255
        self.ocr_engine.recognize_crops([dummy_line])

        # 2. Warmup Layout
        dummy_doc = np.ones((512, 512, 3), dtype=np.uint8) * 255
        self.layout_engine.forward([dummy_doc])

        # 3. Warmup TSR
        dummy_table = np.ones((256, 256, 3), dtype=np.uint8) * 255
        self.table_engine.recognize_structure(dummy_table)

        logger.info("Engine warmup completed.")

    @property
    def ocr_engine(self) -> OcrEngine:
        """Get the OcrEngine instance (lazy-loaded thread-safe)."""
        with self._lock:
            if self._ocr_engine is None:
                self._init_ocr()
            return self._ocr_engine  # type: ignore[return-value]

    @property
    def layout_engine(self) -> LayoutEngine:
        """Get the LayoutEngine instance (lazy-loaded thread-safe)."""
        with self._lock:
            if self._layout_engine is None:
                self._init_layout()
            return self._layout_engine  # type: ignore[return-value]

    @property
    def table_engine(self) -> TableEngine:
        """Get the TableEngine instance (lazy-loaded thread-safe)."""
        with self._lock:
            if self._table_engine is None:
                self._init_table()
            return self._table_engine  # type: ignore[return-value]

    @property
    def is_ready(self) -> bool:
        """Check if all engines are initialized and ready."""
        return (
            self._is_ready
            or (self._ocr_engine is not None and self._layout_engine is not None and self._table_engine is not None)
        )


def get_engine_manager(models_dir: str | Path | None = None) -> EngineManager:
    """Factory helper to obtain the singleton EngineManager."""
    return EngineManager(models_dir=models_dir)
