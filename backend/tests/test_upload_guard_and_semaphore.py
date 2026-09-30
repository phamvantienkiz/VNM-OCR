"""Tests for StreamingUploadGuardMiddleware and OCR semaphore."""

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.middlewares.upload_guard import MAX_UPLOAD_SIZE


def test_upload_guard_rejects_large_content_length():
    """Verify that requests exceeding MAX_UPLOAD_SIZE are rejected immediately with HTTP 413."""
    with TestClient(app) as client:
        # Send a POST with content-length header > 50MB
        headers = {"content-length": str(MAX_UPLOAD_SIZE + 1024)}
        response = client.post("/api/v1/ocr", headers=headers, data=b"fake")
        assert response.status_code == 413
        assert "50MB" in response.json().get("detail", "")


def test_health_check_responds():
    """Verify health endpoint works and responds fast."""
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["models_ready"] is True
