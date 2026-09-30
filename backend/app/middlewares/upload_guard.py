"""Streaming Upload Guard ASGI Middleware.

Provides:
1. Early Backpressure: Rejects new POST upload requests with HTTP 429 when max concurrent slots (10) are reached.
2. Early Header Check: Rejects requests with Content-Length > 50MB immediately with HTTP 413.
3. Stream Chunk Guard: Counts incoming bytes on-the-fly to stop Chunked Transfer Disk DoS, rejecting with HTTP 413.
"""

import asyncio
import logging
from starlette.types import ASGIApp, Scope, Receive, Send
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_CONCURRENT_UPLOADS = 10


class StreamingUploadGuardMiddleware:
    """ASGI Middleware chặn đứng Disk DoS, kiểm soát kích thước Chunked Transfer và Early Backpressure."""

    def __init__(
        self,
        app: ASGIApp,
        max_upload_size: int = MAX_UPLOAD_SIZE,
        max_concurrent: int = MAX_CONCURRENT_UPLOADS,
    ) -> None:
        self.app = app
        self.max_upload_size = max_upload_size
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        # 1. Early Backpressure: Từ chối ngay nếu quá tải kết nối TRƯỚC KHI nhận file
        if self.semaphore.locked():
            response = JSONResponse(
                status_code=429,
                content={"detail": "Hệ thống đang quá tải yêu cầu upload. Vui lòng thử lại sau."},
                headers={"Retry-After": "10"},
            )
            await response(scope, receive, send)
            return

        # 2. Early Header Check: Kiểm tra Content-Length
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                length_int = int(content_length.decode())
                if length_int > self.max_upload_size:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"File quá lớn ({length_int / (1024 * 1024):.1f}MB). Giới hạn tối đa là {self.max_upload_size // (1024 * 1024)}MB."
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        # 3. Stream Chunk Guard: Đếm bytes on-the-fly chống Chunked Transfer Disk DoS
        total_received = 0
        async with self.semaphore:

            async def wrapped_receive():
                nonlocal total_received
                message = await receive()
                if message["type"] == "http.request":
                    body = message.get("body", b"")
                    total_received += len(body)
                    if total_received > self.max_upload_size:
                        raise ValueError("UPLOAD_SIZE_EXCEEDED")
                return message

            try:
                await self.app(scope, wrapped_receive, send)
            except ValueError as e:
                if str(e) == "UPLOAD_SIZE_EXCEEDED":
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"File upload vượt quá giới hạn tối đa {self.max_upload_size // (1024 * 1024)}MB."
                        },
                    )
                    await response(scope, receive, send)
                else:
                    raise
