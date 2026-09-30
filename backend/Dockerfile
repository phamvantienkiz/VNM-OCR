# Multi-stage lightweight Dockerfile for Vietnamese OCR & Document Extraction Backend

# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[cpu,pdf]"

# Stage 2: Runtime stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system runtime libraries required by OpenCV (headless) and ONNX Runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/models && \
    chown -R appuser:appuser /app

# Copy python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy backend application and models
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser models /app/models
COPY --chown=appuser:appuser pyproject.toml README.md /app/

USER appuser

EXPOSE 8000

ENV ENVIRONMENT=production \
    DEBUG=false \
    MODELS_DIR=/app/models \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
