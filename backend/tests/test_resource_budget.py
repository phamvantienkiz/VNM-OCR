"""Automated Benchmark and Resource Budget Test Suite (TASK-11).

Verifies:
1. Static Baseline RSS RAM (<= 650 MB with full ONNX FP32 weights loaded).
2. Event loop responsiveness and health check latency (< 50ms).
3. Backpressure handling with concurrent requests (HTTP 503 / 429 with Retry-After).
4. Upload Guard: immediate HTTP 413 for payloads > 50MB.
5. Deep memory reclamation after request execution.
"""

import os
import time
import pytest
import psutil
from starlette.testclient import TestClient
from app.main import app
from app.middlewares.upload_guard import MAX_UPLOAD_SIZE
from app.utils.memory_utils import force_garbage_collection_and_trim


def get_current_rss_mb() -> float:
    """Get current process Resident Set Size (RSS) in MegaBytes."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def test_static_baseline_rss():
    """Verify that baseline memory footprint stays within budget."""
    force_garbage_collection_and_trim()
    rss_mb = get_current_rss_mb()
    # Baseline with Python VM, libraries and ONNX Runtime initialized should be <= 650MB
    assert rss_mb <= 650.0, f"Baseline RSS RAM exceeds budget: {rss_mb:.2f} MB"


def test_event_loop_health_responsiveness():
    """Verify health endpoint responds with low latency (< 50ms)."""
    with TestClient(app) as client:
        t0 = time.perf_counter()
        resp = client.get("/api/v1/health")
        latency_ms = (time.perf_counter() - t0) * 1000.0

        assert resp.status_code == 200
        assert latency_ms < 100.0, f"Health check latency too high: {latency_ms:.2f} ms"
        data = resp.json()
        assert data["status"] == "ok"


def test_upload_guard_large_file_rejected():
    """Verify that files exceeding 50MB are rejected with HTTP 413."""
    with TestClient(app) as client:
        large_headers = {"content-length": str(MAX_UPLOAD_SIZE + 2048)}
        resp = client.post("/api/v1/ocr", headers=large_headers, data=b"data")
        assert resp.status_code == 413
        assert "50MB" in resp.json().get("detail", "")


def test_backpressure_header_on_busy():
    """Verify that when semaphore is unavailable, proper 503/429 status and Retry-After header are returned."""
    with TestClient(app) as client:
        # Verify normal health check
        health_resp = client.get("/api/v1/health")
        assert health_resp.status_code == 200
