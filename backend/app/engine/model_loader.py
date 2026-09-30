"""ONNX Runtime Model Loader and Session Manager.

Provides thread-safe, optimized loading and caching of ONNX Inference Sessions
with automatic Execution Provider detection (CPU/CUDA) and memory shrinkage.
"""

import logging
from pathlib import Path
from typing import Any
import onnxruntime as ort

import platform
import sys

logger = logging.getLogger(__name__)

# Global cache for loaded (session, run_options) tuples
_LOADED_SESSIONS: dict[str, tuple[ort.InferenceSession, ort.RunOptions]] = {}


def get_preferred_providers(
    device: str = "auto", device_id: int = 0
) -> tuple[list[str], list[dict[str, Any]] | None, str]:
    """Determine the best available ONNX execution providers.

    Args:
        device: 'auto', 'cuda', 'gpu', or 'cpu'.
        device_id: GPU device index.

    Returns:
        tuple of (providers_list, provider_options_list, memory_shrink_tag)
    """
    available_providers = ort.get_available_providers()
    use_cuda = (
        device.lower() in ("auto", "cuda", "gpu")
        and "CUDAExecutionProvider" in available_providers
    )

    if use_cuda:
        cuda_options = {
            "device_id": str(device_id),
            "gpu_mem_limit": str(512 * 1024 * 1024),  # 512 MB memory limit
            "arena_extend_strategy": "kNextPowerOfTwo",
        }
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        provider_options = [cuda_options, {}]
        shrink_tag = f"gpu:{device_id}"
        logger.info("Using CUDAExecutionProvider on GPU device %d", device_id)
    else:
        providers = ["CPUExecutionProvider"]
        provider_options = None
        shrink_tag = "cpu"
        logger.info("Using CPUExecutionProvider")

    return providers, provider_options, shrink_tag


def create_session_options(model_path: Path | None = None) -> ort.SessionOptions:
    """Create optimized SessionOptions for low memory, bounded thread count, and graph caching.

    Args:
        model_path: Optional path to the model file for graph optimization cache discovery.

    Returns:
        Configured ort.SessionOptions instance.
    """
    options = ort.SessionOptions()
    options.enable_cpu_mem_arena = False
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    if model_path and model_path.exists():
        try:
            cache_dir = model_path.parent / ".onnx_opt_cache"
            cache_dir.mkdir(exist_ok=True)

            arch_tag = f"{sys.platform}_{platform.machine()}"
            stat_result = model_path.stat()
            model_tag = f"{stat_result.st_size}_{int(stat_result.st_mtime)}"
            cache_name = f"{model_path.stem}_{arch_tag}_{model_tag}_opt.onnx"
            options.optimized_model_filepath = str(cache_dir / cache_name)
        except PermissionError as e:
            logger.debug("Read-only filesystem detected, skipping ONNX graph disk cache: %s", e)
        except Exception as e:
            logger.warning("Failed to configure ONNX graph cache for %s: %s", model_path.name, e)

    return options


def load_onnx_session(
    model_path: str | Path,
    device: str = "auto",
    device_id: int = 0,
) -> tuple[ort.InferenceSession, ort.RunOptions]:
    """Load an ONNX model file into an InferenceSession with caching and memory shrinkage.

    Args:
        model_path: Path to the .onnx model file.
        device: Execution device ('auto', 'cuda', 'cpu').
        device_id: GPU device ID if using CUDA.

    Returns:
        Tuple of (InferenceSession, RunOptions)

    Raises:
        FileNotFoundError: If the model file does not exist.
    """
    path_obj = Path(model_path).resolve()
    if not path_obj.is_file():
        raise FileNotFoundError(
            f"ONNX model file not found at '{path_obj}'. "
            "Please ensure model weights are present in the models directory."
        )

    cache_key = f"{path_obj}:{device}:{device_id}"
    if cache_key in _LOADED_SESSIONS:
        logger.debug("Reusing cached ONNX session for: %s", cache_key)
        return _LOADED_SESSIONS[cache_key]

    providers, provider_options, shrink_tag = get_preferred_providers(device, device_id)
    session_options = create_session_options(model_path=path_obj)

    session = ort.InferenceSession(
        str(path_obj),
        sess_options=session_options,
        providers=providers,
        provider_options=provider_options,
    )

    run_options = ort.RunOptions()
    if shrink_tag and shrink_tag.startswith("gpu:"):
        run_options.add_run_config_entry("memory.enable_memory_arena_shrinkage", shrink_tag)

    loaded_tuple = (session, run_options)
    _LOADED_SESSIONS[cache_key] = loaded_tuple
    logger.info("Successfully loaded ONNX session: %s (providers=%s)", path_obj.name, session.get_providers())
    return loaded_tuple


def clear_session_cache() -> None:
    """Clear all cached sessions from memory."""
    global _LOADED_SESSIONS
    _LOADED_SESSIONS.clear()
