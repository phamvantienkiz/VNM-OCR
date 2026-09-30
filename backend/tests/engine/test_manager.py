"""Unit tests for EngineManager."""

from pathlib import Path
import pytest
from app.engine.manager import EngineManager, get_engine_manager


def test_engine_manager_singleton():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    mgr1 = EngineManager(models_dir=models_dir, device="cpu")
    mgr2 = get_engine_manager(models_dir=models_dir)
    assert mgr1 is mgr2


def test_engine_manager_check_models():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    missing = EngineManager.check_models_exist(models_dir)
    assert len(missing) == 0

    fake_dir = Path("non_existent_folder_xyz")
    missing_fake = EngineManager.check_models_exist(fake_dir)
    assert len(missing_fake) > 0


def test_engine_manager_initialize_and_warmup():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    mgr = EngineManager(models_dir=models_dir, device="cpu")
    mgr.initialize()
    assert mgr.is_ready is True
    assert mgr.ocr_engine is not None
    assert mgr.layout_engine is not None
    assert mgr.table_engine is not None

    # Run warmup
    mgr.warmup()


def test_engine_manager_clear_and_reset():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    mgr = EngineManager(models_dir=models_dir, device="cpu")
    mgr.initialize()
    assert mgr.is_ready is True
    mgr.clear_sessions()
    assert mgr._ocr_engine is None
    assert mgr.is_ready is False

    EngineManager.reset_singleton()
    assert EngineManager._instance is None
