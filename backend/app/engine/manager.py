"""Engine Lifecycle and Singleton Manager.

Provides centralized access to OCR, Layout, and Table engines with
fail-fast model validation and warmup capabilities.
"""

from pathlib import Path
import logging
import cv2
import numpy as np

from app.core.constants import REQUIRED_MODEL_FILES, DEFAULT_DROP_SCORE
from app.engine.ocr_engine import OcrEngine
from app.engine.layout_engine import LayoutEngine
from app.engine.table_engine import TableEngine

logger = logging.getLogger(__name__)


class EngineManager:
    """Singleton Engine Manager coordinating OCR, Layout, and Table inference engines."""

    _instance: "EngineManager | None" = None

    def __new__(cls, *args, **kwargs) -> "EngineManager":
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

        self.models_dir = Path(models_dir) if models_dir else Path("models")
        self.device = device
        self.device_id = device_id
        self.drop_score = drop_score

        self._ocr_engine: OcrEngine | None = None
        self._layout_engine: LayoutEngine | None = None
        self._table_engine: TableEngine | None = None
        self._is_ready: bool = False
        self._initialized = True

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

    def initialize(self) -> None:
        """Verify models directory and instantiate all engines fail-fast."""
        missing = self.check_models_exist(self.models_dir)
        if missing:
            raise FileNotFoundError(
                f"Missing {len(missing)} required ONNX model file(s) in '{self.models_dir}': {missing}"
            )

        logger.info("Initializing OCR Engine from: %s", self.models_dir)
        self._ocr_engine = OcrEngine(
            models_dir=self.models_dir,
            device=self.device,
            device_id=self.device_id,
            drop_score=self.drop_score,
        )

        logger.info("Initializing Layout Engine from: %s", self.models_dir)
        self._layout_engine = LayoutEngine(
            model_path=self.models_dir / "layout.onnx",
            device=self.device,
            device_id=self.device_id,
        )

        logger.info("Initializing Table Engine from: %s", self.models_dir)
        self._table_engine = TableEngine(
            model_path=self.models_dir / "tsr.onnx",
            device=self.device,
            device_id=self.device_id,
        )

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
        """Get the initialized OcrEngine instance."""
        if self._ocr_engine is None:
            self.initialize()
        return self._ocr_engine  # type: ignore[return-value]

    @property
    def layout_engine(self) -> LayoutEngine:
        """Get the initialized LayoutEngine instance."""
        if self._layout_engine is None:
            self.initialize()
        return self._layout_engine  # type: ignore[return-value]

    @property
    def table_engine(self) -> TableEngine:
        """Get the initialized TableEngine instance."""
        if self._table_engine is None:
            self.initialize()
        return self._table_engine  # type: ignore[return-value]

    @property
    def is_ready(self) -> bool:
        """Check if all engines are initialized and ready."""
        return self._is_ready


def get_engine_manager(models_dir: str | Path | None = None) -> EngineManager:
    """Factory helper to obtain the singleton EngineManager."""
    return EngineManager(models_dir=models_dir)
