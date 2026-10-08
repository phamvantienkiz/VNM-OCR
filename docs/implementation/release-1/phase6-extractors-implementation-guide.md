# Phase 6: Comprehensive Format Extractors — Implementation Guide

> **Mục đích**: Tài liệu này ghi lại **trạng thái hiện tại**, **quyết định đã chốt**, và **hướng dẫn chi tiết từng file cần tạo/sửa** để hoàn thành Phase 6.
> Dùng tài liệu này để tiếp tục implement mà không cần đọc lại toàn bộ context.

---

## 1. Quyết Định Đã Chốt

| # | Câu hỏi | Quyết định |
|---|---------|------------|
| 1 | Tên endpoint auto-routing | **`/extract/auto`** |
| 2 | VNM-OCR endpoint backward-compat | **Giữ cả** `/document/extract` (backward-compatible) **và** `/extract/vnm` (mới). Lý do: `/document/extract` đang được UI frontend gọi, không thể bỏ ngay. |
| 3 | Naming class | **`VNMOCRExtractor`** (ngắn gọn) |

---

## 2. Trạng Thái Hiện Tại (What's Done vs What's Left)

### ✅ Đã hoàn thành

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `services/extractors/base.py` | ✅ Done | BaseExtractor ABC với `name`, `requires_image_input`, `supported_extensions`, `extract()` |
| `services/extractors/__init__.py` | ✅ Done | Import tất cả 4 extractors |
| `services/extractors/native.py` | ✅ Done | NativePDFExtractor — fast path qua pdfplumber |
| `schemas/document.py` | ✅ Done | Thêm `ExtractionMetadata` model và field `metadata` vào `DocumentExtractionResponse` |
| `exceptions/custom.py` | ✅ Done | Thêm `ExtractorNotAvailableError` (501) và `UnsupportedFileFormatError` (415) |

### ❌ Cần tạo mới

| File | Ưu tiên | Mô tả |
|------|---------|-------|
| `services/extractors/vnm.py` | **P0** | VNMOCRExtractor wrapper |
| `services/extractors/docling.py` | P1 | DoclingUniversalExtractor (optional dep) |
| `services/extractors/paddle.py` | P1 | PaddleOCRExtractor (optional dep) |
| `api/v1/endpoints/extract.py` | **P0** | 6 endpoints mới |

### ⚠️ Cần sửa (modify)

| File | Thay đổi |
|------|----------|
| `services/dispatcher.py` | Refactor thành Factory pattern, sử dụng extractors thay vì gọi thẳng DocumentService |
| `api/deps.py` | Thêm DI providers cho extractors |
| `api/v1/router.py` | Include `extract.py` router |

---

## 3. Hướng Dẫn Implement Từng File

### 3.1. `services/extractors/vnm.py` — VNMOCRExtractor

```python
"""VNMOCRExtractor — Vietnamese OCR extraction pipeline wrapper.

Wraps the existing ONNX-based pipeline (DBNet + YOLOv10 + YOLOv8 + VietOCR Seq2Seq)
for high-quality Vietnamese document OCR through the unified Extractor interface.
"""

import logging
import time
from typing import Any, BinaryIO

from app.engine.manager import EngineManager
from app.schemas.document import DocumentExtractionResponse, ExtractionMetadata
from app.services.document_service import DocumentService
from app.services.extractors.base import BaseExtractor
from app.utils.memory_utils import force_garbage_collection_and_trim

logger = logging.getLogger(__name__)


class VNMOCRExtractor(BaseExtractor):
    """Vietnamese OCR Extractor using the full ONNX neural pipeline.

    Pipeline: DBNet (det) → YOLOv10 (layout) → YOLOv8 (tsr) → VietOCR Seq2Seq
    Peak RAM: ~1.5GB during inference.
    """

    def __init__(self, engine_manager: EngineManager) -> None:
        self._document_service = DocumentService(engine_manager=engine_manager)

    @property
    def name(self) -> str:
        return "vnm_ocr"

    @property
    def requires_image_input(self) -> bool:
        return True

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        start_time = time.perf_counter()
        try:
            response = self._document_service.extract_document(
                file_input=file_input,
                extract_tables=extract_tables,
                resolution=resolution,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            response.metadata = ExtractionMetadata(
                pipeline_used=self.name,
                requires_image_input=self.requires_image_input,
                is_vector_recovery=kwargs.get("is_vector_recovery", False),
            )
            response.elapsed_ms = round(elapsed_ms, 2)
            logger.info("VNMOCRExtractor: %d pages, %.2f ms", response.total_pages, elapsed_ms)
            return response
        finally:
            force_garbage_collection_and_trim()
```

**Điểm quan trọng**:
- Nhận `EngineManager` qua constructor (DI).
- Delegate mọi thứ cho `DocumentService.extract_document()` — không duplicate logic.
- Attach `ExtractionMetadata` vào response.
- `is_vector_recovery` được truyền từ dispatcher khi PDF bị lỗi font.

---

### 3.2. `services/extractors/docling.py` — DoclingUniversalExtractor

```python
"""DoclingUniversalExtractor — Office & HTML document extraction.
Optional dependency: docling. Nếu chưa cài → HTTP 501.
"""

import logging
import time
import os
import tempfile
from typing import Any, BinaryIO

from app.exceptions.custom import ExtractorNotAvailableError
from app.schemas.document import (
    DocumentExtractionResponse,
    DocumentPageResult,
    ExtractionMetadata,
)
from app.schemas.ocr import OCRLineResult
from app.services.extractors.base import BaseExtractor
from app.utils.memory_utils import force_garbage_collection_and_trim

logger = logging.getLogger(__name__)


def _check_docling_available() -> bool:
    try:
        import importlib
        importlib.import_module("docling")
        return True
    except ImportError:
        return False


class DoclingUniversalExtractor(BaseExtractor):
    """Extracts content from Office documents and HTML using Docling.

    Supported: .docx, .xlsx, .pptx, .html, .htm
    OCR sub-engines are disabled to minimize RAM.
    """

    @property
    def name(self) -> str:
        return "docling_universal"

    @property
    def requires_image_input(self) -> bool:
        return False

    @property
    def supported_extensions(self) -> set[str]:
        return {".docx", ".xlsx", ".pptx", ".html", ".htm"}

    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        if not _check_docling_available():
            raise ExtractorNotAvailableError(
                extractor_name="DoclingUniversalExtractor",
                install_hint="pip install .[extractors]",
            )

        start_time = time.perf_counter()
        try:
            from docling.document_converter import DocumentConverter

            if hasattr(file_input, "read"):
                file_input.seek(0)
                file_bytes = file_input.read()
                file_input.seek(0)
            else:
                file_bytes = file_input

            filename = kwargs.get("filename", "document.docx")
            suffix = os.path.splitext(filename)[1] or ".docx"

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                converter = DocumentConverter()
                result = converter.convert(tmp_path)
                full_md = result.document.export_to_markdown()

                lines = [line.strip() for line in full_md.splitlines() if line.strip()]
                text_lines = [
                    OCRLineResult(bbox=[[0, 0], [0, 0], [0, 0], [0, 0]], text=line, score=1.0)
                    for line in lines
                ]

                page_res = DocumentPageResult(
                    page_number=1,
                    text_lines=text_lines,
                    layout_regions=[],
                    tables_markdown=[],
                    page_markdown=full_md,
                )

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                return DocumentExtractionResponse(
                    total_pages=1,
                    full_markdown=full_md,
                    pages=[page_res],
                    elapsed_ms=round(elapsed_ms, 2),
                    metadata=ExtractionMetadata(
                        pipeline_used=self.name,
                        requires_image_input=self.requires_image_input,
                    ),
                )
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        finally:
            force_garbage_collection_and_trim()
```

---

### 3.3. `services/extractors/paddle.py` — PaddleOCRExtractor

```python
"""PaddleOCRExtractor — International OCR (English/multi-lang) and Complex VLM.
Optional dependency: paddleocr / paddlex.
"""

import io
import logging
import time
from typing import Any, BinaryIO

from app.exceptions.custom import ExtractorNotAvailableError
from app.schemas.document import (
    DocumentExtractionResponse,
    DocumentPageResult,
    ExtractionMetadata,
)
from app.schemas.ocr import OCRLineResult
from app.services.extractors.base import BaseExtractor
from app.utils.memory_utils import force_garbage_collection_and_trim
from app.utils.pdf_utils import load_document_images

logger = logging.getLogger(__name__)


def _check_paddle_available() -> bool:
    try:
        import importlib
        importlib.import_module("paddleocr")
        return True
    except ImportError:
        return False


class PaddleOCRExtractor(BaseExtractor):
    """PaddleOCR extractor for English/international documents.

    Two modes (selected via kwargs):
      - mode="ocr" (default): PP-OCRv4 for standard text extraction.
      - mode="complex-vlm": PaddleOCR-VL for papers, math, nested tables.
    """

    @property
    def name(self) -> str:
        return "paddle_ocr"

    @property
    def requires_image_input(self) -> bool:
        return True

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

    def extract(
        self,
        file_input: BinaryIO | bytes,
        *,
        extract_tables: bool = True,
        resolution: int = 150,
        **kwargs: Any,
    ) -> DocumentExtractionResponse:
        if not _check_paddle_available():
            raise ExtractorNotAvailableError(
                extractor_name="PaddleOCRExtractor",
                install_hint="pip install .[extractors]  # includes paddleocr",
            )

        mode = kwargs.get("mode", "ocr")
        start_time = time.perf_counter()

        try:
            from paddleocr import PaddleOCR

            ocr_engine = PaddleOCR(use_angle_cls=True, lang="en")

            # Read file bytes
            if hasattr(file_input, "read"):
                file_input.seek(0)
                file_bytes = file_input.read()
                file_input.seek(0)
            else:
                file_bytes = file_input

            # Load document pages as images
            images = load_document_images(file_bytes, resolution=resolution)

            pages_result: list[DocumentPageResult] = []
            page_markdowns: list[str] = []

            for page_idx, page_img in enumerate(images):
                import cv2
                # PaddleOCR expects RGB or path
                rgb_img = cv2.cvtColor(page_img, cv2.COLOR_BGR2RGB)
                result = ocr_engine.ocr(rgb_img, cls=True)

                lines: list[str] = []
                text_lines: list[OCRLineResult] = []

                if result and result[0]:
                    for line in result[0]:
                        box, (text, score) = line
                        lines.append(text)
                        text_lines.append(
                            OCRLineResult(bbox=box, text=text, score=float(score))
                        )

                page_md = "\n".join(lines)
                page_res = DocumentPageResult(
                    page_number=page_idx + 1,
                    text_lines=text_lines,
                    layout_regions=[],
                    tables_markdown=[],
                    page_markdown=page_md,
                )
                pages_result.append(page_res)
                page_markdowns.append(page_md)

                del rgb_img, page_img

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            full_markdown = "\n\n---\n\n".join([pm for pm in page_markdowns if pm.strip()])

            pipeline_name = "paddle_complex_vlm" if mode == "complex-vlm" else self.name

            return DocumentExtractionResponse(
                total_pages=len(pages_result),
                full_markdown=full_markdown,
                pages=pages_result,
                elapsed_ms=round(elapsed_ms, 2),
                metadata=ExtractionMetadata(
                    pipeline_used=pipeline_name,
                    requires_image_input=self.requires_image_input,
                ),
            )
        finally:
            force_garbage_collection_and_trim()
```

---

### 3.4. `services/dispatcher.py` — Refactor thành Extractor-based

```python
"""Universal Document Dispatcher Module.

Routes incoming documents through capability-based extractors using the
Strategy Pattern. SmartPDFInspector classifies → select best extractor → execute.
"""

import io
import logging
from typing import Any, BinaryIO

from app.engine.manager import EngineManager
from app.services.inspector import SmartPDFInspector, PageType
from app.services.extractors.base import BaseExtractor
from app.services.extractors.native import NativePDFExtractor
from app.services.extractors.vnm import VNMOCRExtractor
from app.schemas.document import DocumentExtractionResponse, ExtractionMetadata
from app.utils.image_utils import is_pdf_file

logger = logging.getLogger(__name__)


class UniversalDocumentDispatcher:
    """Routes documents to the optimal extractor based on SmartPDFInspector analysis."""

    def __init__(self, engine_manager: EngineManager) -> None:
        self._engine_manager = engine_manager
        self._native_extractor = NativePDFExtractor()
        self._vnm_extractor = VNMOCRExtractor(engine_manager=engine_manager)

    def _select_extractor(
        self, classification: PageType
    ) -> tuple[BaseExtractor, dict[str, Any]]:
        """Select the best extractor and extra kwargs based on classification."""
        if classification == PageType.DIGITAL_DOCUMENT:
            return self._native_extractor, {}
        elif classification == PageType.CORRUPTED_VECTOR:
            return self._vnm_extractor, {"is_vector_recovery": True}
        else:
            # SCANNED_DOCUMENT, COMPLEX_DOCUMENT → VNM OCR pipeline
            return self._vnm_extractor, {}

    def dispatch(
        self,
        file_input: BinaryIO | bytes,
        extract_tables: bool = True,
        resolution: int = 150,
    ) -> DocumentExtractionResponse:
        """Classify → select extractor → execute → return response with metadata."""
        # Detect PDF
        is_pdf = False
        if hasattr(file_input, "read"):
            file_input.seek(0)
            is_pdf = is_pdf_file(file_input)
            file_input.seek(0)
        else:
            is_pdf = file_input.startswith(b"%PDF")

        classification = PageType.SCANNED_DOCUMENT

        if is_pdf:
            try:
                profiles = SmartPDFInspector.inspect(file_input)
                classification = SmartPDFInspector.classify_document(profiles)
                logger.info("SmartPDFInspector → %s", classification.value)
            except Exception as e:
                logger.warning("Inspector failed, fallback Heavy Path: %s", e)

        extractor, extra_kwargs = self._select_extractor(classification)

        response = extractor.extract(
            file_input,
            extract_tables=extract_tables,
            resolution=resolution,
            **extra_kwargs,
        )

        # Enrich metadata with classification
        if response.metadata:
            response.metadata.classification = classification.value
        else:
            response.metadata = ExtractionMetadata(
                pipeline_used=extractor.name,
                classification=classification.value,
            )

        return response
```

**Thay đổi so với bản cũ**:
- Constructor nhận `EngineManager` thay vì `DocumentService`.
- Return `DocumentExtractionResponse` trực tiếp (không còn tuple).
- Logic routing dựa trên `_select_extractor()`.

---

### 3.5. `api/v1/endpoints/extract.py` — 6 Endpoints mới

```python
"""Explicit Format Extraction Endpoints (Phase 6).

Endpoints:
  POST /extract/auto              — Smart auto-routing
  POST /extract/native/pdf        — Born-digital PDF only
  POST /extract/docling           — Office & HTML
  POST /extract/paddle/ocr        — English/International OCR
  POST /extract/paddle/complex-vlm — Paper/Math VLM
  POST /extract/vnm               — Vietnamese OCR (ONNX pipeline)
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, Query, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import (
    get_dispatcher,
    get_vnm_extractor,
    get_native_extractor,
    get_docling_extractor,
    get_paddle_extractor,
)
from app.services.dispatcher import UniversalDocumentDispatcher
from app.services.extractors.native import NativePDFExtractor
from app.services.extractors.vnm import VNMOCRExtractor
from app.services.extractors.docling import DoclingUniversalExtractor
from app.services.extractors.paddle import PaddleOCRExtractor
from app.schemas.document import DocumentExtractionResponse

router = APIRouter(prefix="/extract", tags=["Extract"])


async def _run_with_semaphore(
    request: Request,
    sync_fn: Any,
    *,
    timeout_acquire: float = 10.0,
    timeout_process: float = 120.0,
    **kwargs: Any,
) -> Any:
    """Acquire OCR semaphore → run sync function in thread → handle timeouts."""
    ocr_sem: asyncio.Semaphore = (
        getattr(request.app.state, "ocr_semaphore", None) or asyncio.Semaphore(1)
    )
    ocr_acquired = False
    try:
        try:
            async with asyncio.timeout(timeout_acquire):
                await ocr_sem.acquire()
                ocr_acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Hệ thống OCR đang bận. Vui lòng thử lại sau."},
                headers={"Retry-After": "30"},
            )

        try:
            async with asyncio.timeout(timeout_process):
                return await asyncio.to_thread(sync_fn, **kwargs)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý (Processing Timeout)."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()


def _validate_file(file: UploadFile) -> None:
    """Validate that a file was actually uploaded."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )


# ── 1. Auto-routing endpoint ────────────────────────────────────────

@router.post(
    "/auto",
    response_model=DocumentExtractionResponse,
    summary="Auto-classify & extract document",
    description=(
        "Automatically classifies the document type via SmartPDFInspector and routes "
        "to the optimal extraction pipeline. Returns pipeline_used in metadata."
    ),
)
async def extract_auto(
    request: Request,
    file: UploadFile = File(..., description="PDF or image file"),
    extract_tables: bool = Query(True, description="Extract tables to Markdown"),
    resolution: int = Query(150, ge=72, le=300, description="PDF rendering DPI"),
    dispatcher: UniversalDocumentDispatcher = Depends(get_dispatcher),
) -> Any:
    _validate_file(file)
    await file.seek(0)
    result = await _run_with_semaphore(
        request,
        dispatcher.dispatch,
        file_input=file.file,
        extract_tables=extract_tables,
        resolution=resolution,
    )
    await file.close()
    return result


# ── 2. Native PDF ───────────────────────────────────────────────────

@router.post(
    "/native/pdf",
    response_model=DocumentExtractionResponse,
    summary="Born-digital PDF fast extraction (< 50ms/page)",
)
async def extract_native_pdf(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    extractor: NativePDFExtractor = Depends(get_native_extractor),
) -> Any:
    _validate_file(file)
    await file.seek(0)
    result = await _run_with_semaphore(
        request,
        extractor.extract,
        file_input=file.file,
        extract_tables=extract_tables,
        timeout_process=30.0,
    )
    await file.close()
    return result


# ── 3. Docling (Office & HTML) ──────────────────────────────────────

@router.post(
    "/docling",
    response_model=DocumentExtractionResponse,
    summary="Office & HTML extraction via Docling",
)
async def extract_docling(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    extractor: DoclingUniversalExtractor = Depends(get_docling_extractor),
) -> Any:
    _validate_file(file)
    await file.seek(0)
    result = await _run_with_semaphore(
        request,
        extractor.extract,
        file_input=file.file,
        extract_tables=extract_tables,
        filename=file.filename,
        timeout_process=60.0,
    )
    await file.close()
    return result


# ── 4. PaddleOCR (English/International) ────────────────────────────

@router.post(
    "/paddle/ocr",
    response_model=DocumentExtractionResponse,
    summary="English/International OCR via PaddleOCR",
)
async def extract_paddle_ocr(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    resolution: int = Query(150, ge=72, le=300),
    extractor: PaddleOCRExtractor = Depends(get_paddle_extractor),
) -> Any:
    _validate_file(file)
    await file.seek(0)
    result = await _run_with_semaphore(
        request,
        extractor.extract,
        file_input=file.file,
        extract_tables=extract_tables,
        resolution=resolution,
        mode="ocr",
    )
    await file.close()
    return result


# ── 5. PaddleOCR Complex VLM (Paper/Math) ───────────────────────────

@router.post(
    "/paddle/complex-vlm",
    response_model=DocumentExtractionResponse,
    summary="Paper/Math extraction via PaddleOCR-VL",
)
async def extract_paddle_vlm(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    resolution: int = Query(150, ge=72, le=300),
    extractor: PaddleOCRExtractor = Depends(get_paddle_extractor),
) -> Any:
    _validate_file(file)
    await file.seek(0)
    result = await _run_with_semaphore(
        request,
        extractor.extract,
        file_input=file.file,
        extract_tables=extract_tables,
        resolution=resolution,
        mode="complex-vlm",
        timeout_process=180.0,
    )
    await file.close()
    return result


# ── 6. Vietnamese OCR ───────────────────────────────────────────────

@router.post(
    "/vnm",
    response_model=DocumentExtractionResponse,
    summary="Vietnamese OCR (ONNX pipeline: DBNet + YOLO + VietOCR)",
)
async def extract_vnm(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(True),
    resolution: int = Query(150, ge=72, le=300),
    extractor: VNMOCRExtractor = Depends(get_vnm_extractor),
) -> Any:
    _validate_file(file)
    await file.seek(0)
    result = await _run_with_semaphore(
        request,
        extractor.extract,
        file_input=file.file,
        extract_tables=extract_tables,
        resolution=resolution,
    )
    await file.close()
    return result
```

---

### 3.6. `api/deps.py` — Thêm DI providers

Append vào cuối file hiện tại (sau `get_dispatcher_service`):

```python
# ── Phase 6: Extractor DI Providers ─────────────────────────────────

def get_native_extractor() -> "NativePDFExtractor":
    """DI provider for NativePDFExtractor (no engine needed)."""
    from app.services.extractors.native import NativePDFExtractor
    return NativePDFExtractor()


def get_vnm_extractor(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> "VNMOCRExtractor":
    """DI provider for VNMOCRExtractor (needs EngineManager for ONNX models)."""
    from app.services.extractors.vnm import VNMOCRExtractor
    return VNMOCRExtractor(engine_manager=manager)


def get_docling_extractor() -> "DoclingUniversalExtractor":
    """DI provider for DoclingUniversalExtractor (optional dependency)."""
    from app.services.extractors.docling import DoclingUniversalExtractor
    return DoclingUniversalExtractor()


def get_paddle_extractor() -> "PaddleOCRExtractor":
    """DI provider for PaddleOCRExtractor (optional dependency)."""
    from app.services.extractors.paddle import PaddleOCRExtractor
    return PaddleOCRExtractor()


def get_dispatcher(
    manager: EngineManager = Depends(get_engine_manager_dep),
) -> "UniversalDocumentDispatcher":
    """DI provider for the refactored UniversalDocumentDispatcher."""
    from app.services.dispatcher import UniversalDocumentDispatcher
    return UniversalDocumentDispatcher(engine_manager=manager)
```

> **Lưu ý**: Hàm `get_dispatcher_service` cũ vẫn giữ lại (backward-compat cho `/document/smart-extract`), nhưng nội bộ nó cần cập nhật constructor của `UniversalDocumentDispatcher`.

---

### 3.7. `api/v1/router.py` — Include extract router

```python
"""API v1 Main Router."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, ocr, layout, table, document, extract

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ocr.router, tags=["OCR"])
api_router.include_router(layout.router, tags=["Layout"])
api_router.include_router(table.router, tags=["Table"])
api_router.include_router(document.router, tags=["Document"])
api_router.include_router(extract.router, tags=["Extract"])
```

---

## 4. Backward Compatibility: `/document/extract`

Endpoint `/document/extract` trong `document.py` **giữ nguyên không đổi**. Nó tiếp tục gọi thẳng `DocumentService.extract_document()` như hiện tại.

Endpoint mới `/extract/vnm` cũng gọi cùng pipeline nhưng qua `VNMOCRExtractor` wrapper, có thêm `ExtractionMetadata` trong response.

Endpoint `/document/smart-extract` cũ cũng giữ lại nhưng **cần cập nhật** `get_dispatcher_service` trong `deps.py` vì constructor mới nhận `EngineManager` thay vì `DocumentService`. Cập nhật:

```python
# Sửa get_dispatcher_service cũ:
def get_dispatcher_service(
    manager: EngineManager = Depends(get_engine_manager_dep),
):
    from app.services.dispatcher import UniversalDocumentDispatcher
    return UniversalDocumentDispatcher(engine_manager=manager)
```

Và cập nhật `document.py` endpoint `smart_extract_document` — bỏ logic unpack tuple vì `dispatch()` giờ return response trực tiếp:

```python
# Thay đổi trong smart_extract_document:
# Cũ:  response, metadata = await asyncio.to_thread(dispatcher.dispatch, ...)
#       res_dict = response.model_dump()
#       res_dict["metadata"] = metadata

# Mới: response = await asyncio.to_thread(dispatcher.dispatch, ...)
#       return response  # metadata đã nằm trong response.metadata
```

---

## 5. Thứ Tự Thực Hiện (Execution Order)

```text
Step 1:  Tạo vnm.py              (copy code mục 3.1)
Step 2:  Tạo docling.py          (copy code mục 3.2)
Step 3:  Tạo paddle.py           (copy code mục 3.3)
Step 4:  Sửa dispatcher.py       (overwrite toàn bộ theo mục 3.4)
Step 5:  Sửa deps.py             (append mục 3.6 + sửa get_dispatcher_service)
Step 6:  Tạo extract.py endpoint (copy code mục 3.5)
Step 7:  Sửa router.py           (thêm import + include, mục 3.7)
Step 8:  Sửa document.py         (update smart_extract_document, mục 4)
Step 9:  Test import:   python -c "from app.services.extractors import *"
Step 10: Test server:   uvicorn app.main:app --reload
```

---

## 6. Checklist Cuối Cùng

- [ ] `vnm.py` tạo xong
- [ ] `docling.py` tạo xong
- [ ] `paddle.py` tạo xong
- [ ] `dispatcher.py` refactored (nhận EngineManager, return response trực tiếp)
- [ ] `deps.py` updated (5 providers mới + sửa `get_dispatcher_service`)
- [ ] `extract.py` endpoint created (6 endpoints)
- [ ] `router.py` updated (include extract)
- [ ] `document.py` updated (smart_extract không unpack tuple)
- [ ] `__init__.py` import không lỗi
- [ ] `/extract/auto` hoạt động
- [ ] `/extract/vnm` hoạt động
- [ ] `/document/extract` backward-compatible

---

## 7. Lưu Ý Kỹ Thuật

- **Memory**: Mỗi extractor phải gọi `force_garbage_collection_and_trim()` trong `finally` block.
- **Semaphore**: Tất cả endpoints GPU/ONNX đi qua `ocr_semaphore` (1 concurrent task).
- **Dependencies isolation**: `docling` và `paddleocr` là optional group `[extractors]` trong `pyproject.toml`. Không force install.
- **Schema**: `DocumentExtractionResponse.model_config` có `extra="forbid"` nhưng `ExtractionMetadata` có `extra="allow"` để extractor có thể thêm metadata tùy chỉnh.
- **Error codes**: `ExtractorNotAvailableError` → HTTP 501, `UnsupportedFileFormatError` → HTTP 415.
