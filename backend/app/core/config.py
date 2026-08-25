"""Application Configuration module using Pydantic Settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for the backend service."""

    APP_NAME: str = "Vietnamese OCR & Document Extraction Service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Origins
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://localhost:5173",
    ]

    # Models & Inference Settings
    MODELS_DIR: str = "models"
    DEFAULT_DEVICE: str = "auto"  # 'auto', 'cpu', or 'cuda'
    DROP_SCORE: float = 0.5
    MAX_IMAGE_SIZE: int = 960

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_models_dir(self) -> Path:
        """Resolve the absolute path to the models directory."""
        path = Path(self.MODELS_DIR)
        if not path.is_absolute():
            backend_root = Path(__file__).resolve().parents[2]
            path = backend_root / path
        return path


settings = Settings()
