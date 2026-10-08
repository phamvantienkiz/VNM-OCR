"""Unit tests for Phase 5 - Hardware Matrix & On-Demand Lazy Loading."""

from pathlib import Path
from app.engine.manager import EngineManager


def test_on_demand_lazy_loading():
    """Verify that EngineManager only loads the requested engine and not all models."""
    EngineManager.reset_singleton()
    models_dir = Path(__file__).resolve().parents[1] / "models"
    mgr = EngineManager(models_dir=models_dir, device="cpu")

    # Before accessing any engine, none should be loaded
    assert mgr._ocr_engine is None
    assert mgr._layout_engine is None
    assert mgr._table_engine is None

    # Access ONLY layout engine
    layout = mgr.layout_engine
    assert layout is not None
    assert mgr._layout_engine is not None

    # OCR and Table engines MUST still be None (saving RAM/VRAM)
    assert mgr._ocr_engine is None
    assert mgr._table_engine is None

    # Clean up
    mgr.clear_sessions()
    EngineManager.reset_singleton()
