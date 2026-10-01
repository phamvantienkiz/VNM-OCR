"""Custom Domain Exceptions."""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 400, error_code: str = "APP_ERROR") -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ModelNotFoundError(AppException):
    """Raised when required model weights are missing."""

    def __init__(self, message: str = "Required ONNX model weights not found") -> None:
        super().__init__(message=message, status_code=500, error_code="MODEL_NOT_FOUND")


class InvalidFileFormatError(AppException):
    """Raised when an uploaded file is corrupted or unsupported."""

    def __init__(self, message: str = "Invalid or unsupported document/image format") -> None:
        super().__init__(message=message, status_code=400, error_code="INVALID_FILE_FORMAT")


class InferenceError(AppException):
    """Raised when model inference fails."""

    def __init__(self, message: str = "Error during model execution") -> None:
        super().__init__(message=message, status_code=500, error_code="INFERENCE_ERROR")


class ExtractorNotAvailableError(AppException):
    """Raised when an optional extractor's dependencies are not installed."""

    def __init__(self, extractor_name: str, install_hint: str = "pip install .[extractors]") -> None:
        message = (
            f"Extractor '{extractor_name}' is not available because its dependencies are not installed. "
            f"Install with: {install_hint}"
        )
        super().__init__(message=message, status_code=501, error_code="EXTRACTOR_NOT_AVAILABLE")


class UnsupportedFileFormatError(AppException):
    """Raised when a file format is not supported by the chosen extractor."""

    def __init__(self, message: str = "File format is not supported by this extractor") -> None:
        super().__init__(message=message, status_code=415, error_code="UNSUPPORTED_FILE_FORMAT")
