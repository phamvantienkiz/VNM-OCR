"""Unit tests for ONNX Model Loader."""

from pathlib import Path
import pytest
from app.engine.model_loader import (
    load_onnx_session,
    get_preferred_providers,
    clear_session_cache,
)


def test_get_preferred_providers_cpu():
    providers, options, tag = get_preferred_providers("cpu")
    assert providers == ["CPUExecutionProvider"]
    assert options is None
    assert tag == "cpu"


def test_load_onnx_session_success():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    det_model = models_dir / "det.onnx"
    if not det_model.exists():
        pytest.skip(f"Model {det_model} does not exist for testing")

    session, run_options = load_onnx_session(det_model, device="cpu")
    assert session is not None
    assert run_options is not None
    assert len(session.get_inputs()) > 0
    assert len(session.get_outputs()) > 0


def test_load_onnx_session_caching():
    models_dir = Path(__file__).resolve().parents[2] / "models"
    det_model = models_dir / "det.onnx"
    if not det_model.exists():
        pytest.skip("Model does not exist")

    sess1, _ = load_onnx_session(det_model, device="cpu")
    sess2, _ = load_onnx_session(det_model, device="cpu")
    assert sess1 is sess2


def test_load_onnx_session_file_not_found():
    with pytest.raises(FileNotFoundError) as exc_info:
        load_onnx_session("non_existent_model_file.onnx")
    assert "ONNX model file not found" in str(exc_info.value)


def test_clear_session_cache():
    clear_session_cache()
    # Cache should be empty without error
