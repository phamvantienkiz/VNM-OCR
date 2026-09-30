"""Global Exception Handlers for FastAPI."""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions.custom import AppException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning("Application error: %s (code=%s)", exc.message, exc.error_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": exc.error_code,
                "detail": exc.message,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("Validation/Value error: %s", str(exc))
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_code": "INVALID_VALUE",
                "detail": str(exc),
            },
        )

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        logger.error("File not found: %s", str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "FILE_NOT_FOUND",
                "detail": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "detail": f"An unexpected error occurred: {str(exc)}",
            },
        )
