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


def test_create_session_options_defaults():
    from app.engine.model_loader import create_session_options
    import onnxruntime as ort

    opts = create_session_options()
    assert opts.enable_cpu_mem_arena is False
    assert opts.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL
    assert opts.intra_op_num_threads == 2
    assert opts.inter_op_num_threads == 1
    assert opts.graph_optimization_level == ort.GraphOptimizationLevel.ORT_ENABLE_ALL


def test_create_session_options_with_model_path():
    from app.engine.model_loader import create_session_options

    models_dir = Path(__file__).resolve().parents[2] / "models"
    det_model = models_dir / "det.onnx"
    if not det_model.exists():
        pytest.skip("det.onnx not found for test")

    opts = create_session_options(model_path=det_model)
    assert opts.optimized_model_filepath != ""
    assert ".onnx_opt_cache" in opts.optimized_model_filepath
    assert "det_" in opts.optimized_model_filepath

