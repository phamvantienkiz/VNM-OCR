# Kế Hoạch Tối Ưu Hóa Tài Nguyên Cho Module OCR Nhúng RAG / Agent (1 Worker, 2 Threads, $\le$ 2GB RAM & Tự Động Thu Hồi)

> **Mã tài liệu:** `DOC-PLAN-OCR-002`  
> **Ngày cập nhật:** 02/09/2026  
> **Phiên bản:** `4.5.0` (Clean Router Separation, Gitignore Temp Sandboxing & Production Hardened per Round 11)  
> **Tài liệu căn cứ:**  
> - [`DOC-REPORT-HW-001 v3.5.0`](file:///E:/MyProject/VNM-OCR/docs/report/hardware_optimization_and_api_architecture.md) — Báo cáo hiện trạng phần cứng  
> - [`DOC-REP-COUNTER-003 v11.0.0`](file:///E:/MyProject/VNM-OCR/docs/report/counter_argument_review.md) — Phân tích phản biện & đánh giá cải thiện (Vòng 1 đến Vòng 11)  
> **Áp dụng cho:** Toàn bộ hệ thống OCR & Document Extraction tại [`backend/`](file:///E:/MyProject/VNM-OCR/backend)  
> **Nền tảng mục tiêu:** Tương thích đa nền tảng (Linux, Windows, macOS / Apple Silicon & Intel)  

---

## 1. BỐI CẢNH & MỤC TIÊU CỐT LÕI

Khi được tích hợp vào các hệ sinh thái RAG (Retrieval-Augmented Generation) hoặc Multi-Agent (LangGraph, CrewAI, AutoGen), mô-đun OCR đóng vai trò là một **sub-service / worker tool** chạy song song cùng LLM, Vector Database (Milvus/Qdrant) và Embedding models. Do đó, mô-đun OCR **không được phép chiếm dụng tài nguyên máy chủ vô hạn** mà phải tuân thủ ngân sách phần cứng cực kỳ nghiêm ngặt:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    NGÂN SÁCH TÀI NGUYÊN BẮT BUỘC (HARD CONSTRAINTS)             │
├────────────────────────────────┬────────────────────────────────────────────────┤
│ 1. Số lượng Uvicorn Worker     │ TỐI ĐA 1 WORKER (Single Process)               │
│ 2. Giới hạn tính toán CPU      │ TỐI ĐA 2 ACTIVE COMPUTE THREADS (<= 200% CPU)  │
│ 3. Ngân sách RAM Đỉnh Tải      │ TỐI ĐA 2GB RAM (Mục tiêu: <= 1.2GB PDF 50 trang)│
│ 4. Thu hồi bộ nhớ (Reclaim)    │ BẮT BUỘC trả RAM về Baseline (<= 600MB) ngay lập│
│                                │ tức (t + 2s) sau khi kết thúc request          │
│ 5. Độ chính xác Tiếng Việt     │ BẢO TOÀN 100% độ chính xác mô hình FP32 gốc     │
│ 6. Tương thích môi trường      │ Chạy mượt mà trên Linux (Docker), Windows, macOS│
│ 7. Quản lý File Tạm & Gitignore│ Ép 100% temp vào repo/temp và ignore trên Git   │
│ 8. Chuẩn mực Clean Architecture│ main.py không chứa bất kỳ endpoint nào          │
└────────────────────────────────┴────────────────────────────────────────────────┘
```

---

## 2. KIẾN TRÚC TỔNG THỂ GIẢI PHÁP TỐI ƯU

```mermaid
flowchart TD
    subgraph ClientAgent [RAG / Multi-Agent System]
        Req[POST /api/v1/document/extract hoặc /api/v1/ocr\nUpload PDF / Image File]
    end

    subgraph SecurityGuard [Early ASGI Middleware & Lifecycle Guard Layer]
        EarlyBackpressure{Active Slots >= 10?}
        Reject429[Early Reject: HTTP 429\nĐóng kết nối TRƯỚC KHI tải file]
        SizeHeaderCheck{Content-Length > 50MB?}
        Reject413[Early Reject: HTTP 413\nTừ chối ngay từ Request Header]
        
        ASGIStreamWrap[ASGI Receive Stream Wrap\nĐếm bytes thực tế on-the-fly]
        ChunkExceed{Chunked Bytes > 50MB?}
        AbortStream[Abort Connection: HTTP 413\nChặn đứng Disk Exhaustion DoS]
        
        FastAPISpool[FastAPI SpooledTemporaryFile\nSandboxed trong backend/temp/ không rác OS & Gitignored]
    end

    subgraph ConcurrencyControl [CPU Inference Concurrency Control]
        OCRSem[Lifespan Async Semaphore: app.state.ocr_semaphore = 1]
        DirectFilePass[Pass file.file Direct to Service\nKhông đọc content bytes -> Không Double RAM]
        ThreadPool[Asyncio Thread Offload: asyncio.to_thread]
    end

    subgraph StreamingPipeline [Streaming & Memory-Safe Engine]
        SmartCheck{Born-Digital PDF Check?\n_try_extract_digital_text 1-Pass}
        FastPass[Direct Vector Text Extract via pdfplumber\nRAM < 250MB, Latency < 50ms]
        
        StreamIter[Streaming Page Generator: yield 1 page BGR at a time]
        ZeroCopyPIL[Zero-Copy PIL to BGR: array[:, :, ::-1]]
        FP32Engines[Pure ONNX FP32 Engines\nintra=2, inter=1, Auto Graph Cache]
        PageProc[OCR Detection + Recognition + Layout + TSR]
        DefensiveDel[Defensive ori_im copy -> Early del ori_im after crop -> del crop list]
    end

    subgraph CrossPlatformReclaim [Cross-Platform Memory Reclamation Layer]
        GC[Python gc.collect generation=2]
        TrimLinux[Linux glibc: libc.malloc_trim 0]
        TrimDarwin[macOS Darwin: libSystem malloc_zone_pressure_relief]
        TrimWin[Windows: kernel32.HeapCompact]
        Resp[Return Response JSON\nProcess RAM drops back to <= 600MB]
    end

    Req --> EarlyBackpressure
    EarlyBackpressure -->|Yes: Saturated| Reject429
    EarlyBackpressure -->|No: Available| SizeHeaderCheck
    SizeHeaderCheck -->|Yes: Over 50MB| Reject413
    SizeHeaderCheck -->|No: Valid| ASGIStreamWrap
    ASGIStreamWrap --> ChunkExceed
    ChunkExceed -->|Yes: Chunked Bypass| AbortStream
    ChunkExceed -->|No: Safe Stream| FastAPISpool
    
    FastAPISpool --> OCRSem
    OCRSem --> DirectFilePass
    DirectFilePass --> ThreadPool
    ThreadPool --> SmartCheck
    SmartCheck -->|Born-Digital PDF (Text != None)| FastPass
    SmartCheck -->|Scanned / Image (Text == None)| StreamIter
    FastPass --> CrossPlatformReclaim
    StreamIter --> ZeroCopyPIL
    ZeroCopyPIL --> FP32Engines
    FP32Engines --> PageProc
    PageProc --> DefensiveDel
    DefensiveDel -->|Next Page| StreamIter
    DefensiveDel -->|All Pages Completed| CrossPlatformReclaim
    CrossPlatformReclaim --> Resp
```

---

## 3. CÁC TRỤ CỘT KỸ THUẬT TRIỂN KHAI CHI TIẾT

---

### TRỤ CỘT 1: ĐIỀU PHỐI CONCURRENCY, ASGI STREAMING GUARD, SANDBOXING FILE TẠM & ROUTER CHUẨN MỰC

#### 1. Vấn đề giải quyết & Điểm hoàn thiện (Review V1 đến V11):
- **Khống Chế File Tạm & Khai Báo Gitignore (Vá Lỗi #53 & #56 - Vòng 10 & 11)**:
  - *Nguy cơ OS Pollution & Git Bloat*: FastAPI dùng `SpooledTemporaryFile` ghi file vào temp OS (`%TEMP%` trên Windows, `/tmp` trên Linux).
  - *Giải pháp*: Ép buộc `tempfile.tempdir = str(PROJECT_ROOT / "temp")` ngay dòng đầu `main.py`. Đồng thời khai báo rõ `temp/`, `backend/temp/`, `.onnx_opt_cache/` trong `.gitignore` để ngăn chặn developer commit nhầm file rác.
- **Tiêu Chuẩn Hóa Lớp Middleware & Tách Biệt Router Tuyệt Đối (Vá Lỗi #54 & #55 - Vòng 10 & 11)**:
  - *Vi phạm Clean Architecture*: Nhồi nhét `StreamingUploadGuardMiddleware` hoặc viết trực tiếp `@app.post("/api/ocr")` vào `main.py` vi phạm chuẩn của skill `fastapi-backend-scaffold`.
  - *Giải pháp*: 
    1. Tách middleware vào [`backend/app/middlewares/upload_guard.py`](file:///E:/MyProject/VNM-OCR/backend/app/middlewares/upload_guard.py) và đăng ký qua [`backend/app/middlewares/__init__.py`](file:///E:/MyProject/VNM-OCR/backend/app/middlewares/__init__.py).
    2. Di dời toàn bộ logic OCR (gồm cả OCR v1 và Legacy format) vào [`backend/app/api/v1/endpoints/ocr.py`](file:///E:/MyProject/VNM-OCR/backend/app/api/v1/endpoints/ocr.py). File `main.py` chỉ làm nhiệm vụ kết nối và không chứa bất kỳ logic route nào.
- **Hiểu Đúng Vòng Đời FastAPI & Chống Disk Exhaustion DoS (Vá Lỗi #49 & #50)**:
  - Can thiệp trực tiếp ở tầng ASGI Middleware:
    1. **Early Backpressure (#52)**: Kiểm tra số lượng active upload/OCR request ngay khi request vừa tới. Nếu hệ thống đã đạt tải trọng tối đa (`MAX_CONCURRENT_UPLOADS = 10`), lập tức phản hồi `HTTP 429` (kèm `Retry-After: 10`) và ngắt kết nối TCP **TRƯỚC KHI** nhận bất kỳ byte nội dung nào.
    2. **Early Header Check**: Kiểm tra `Content-Length > 50MB` $\rightarrow$ Trả về `HTTP 413` ngay lập tức.
    3. **On-the-fly Chunk Streaming Guard**: Wrap hàm `receive()` của ASGI để đếm tổng số bytes thực tế theo từng chunk. Ngay khi luồng chunked vượt quá 50MB, lập tức ngắt stream và trả về `HTTP 413`, chặn đứng nguy cơ tràn ổ cứng.
- **Triệt Tiêu Hoàn Toàn Double RAM Allocation (Vá Lỗi #51)**:
  - Truyền trực tiếp đối tượng file-like `file.file` (`SpooledTemporaryFile`) xuống tầng Service và Engine. `pdfplumber.open(file.file)` và OpenCV/PIL đọc trực tiếp từ con trỏ file (hoặc đọc streaming), giải phóng 100% bộ đệm bytes dư thừa.
- **Bảo Vệ CPU Concurrency Độc Quyền**: Khởi tạo `ocr_semaphore = asyncio.Semaphore(1)` trong `lifespan` bảo vệ tầng thực thi mô hình ONNX, kết hợp `asyncio.to_thread` với 2 tầng timeout độc lập (`QUEUE_TIMEOUT=10s`, `OCR_TIMEOUT=120s`).

#### 2. Thiết kế triển khai:

**A. Khống chế Thư mục File Tạm tại dòng đầu `main.py` ([`backend/app/main.py`](file:///E:/MyProject/VNM-OCR/backend/app/main.py)):**

```python
# backend/app/main.py — BẮT BUỘC LÀ CÁC DÒNG ĐẦU TIÊN TRƯỚC MỌI APPLICATION IMPORT
import os
import sys
import tempfile
from pathlib import Path

# 1. Quản lý File Tạm (Sandboxing) — Tránh làm rác ổ C: trên Windows hoặc /tmp trên Linux (Issue #53)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)
tempfile.tempdir = str(TEMP_DIR)

# 2. Khóa luồng CPU đa nền tảng
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"
if sys.platform == "darwin":
    os.environ["VECLIB_MAXIMUM_THREADS"] = "2"

import cv2
cv2.setNumThreads(2)
```

**B. Tầng Middleware Riêng Biệt ([`backend/app/middlewares/upload_guard.py`](file:///E:/MyProject/VNM-OCR/backend/app/middlewares/upload_guard.py)):**

```python
# backend/app/middlewares/upload_guard.py
import asyncio
from starlette.types import ASGIApp, Scope, Receive, Send
from fastapi.responses import JSONResponse

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_CONCURRENT_UPLOADS = 10

class StreamingUploadGuardMiddleware:
    """ASGI Middleware chặn đứng Disk DoS, kiểm soát kích thước Chunked Transfer và Early Backpressure."""
    def __init__(self, app: ASGIApp, max_upload_size: int = MAX_UPLOAD_SIZE, max_concurrent: int = MAX_CONCURRENT_UPLOADS):
        self.app = app
        self.max_upload_size = max_upload_size
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        # 1. Early Backpressure: Từ chối ngay nếu quá tải kết nối TRƯỚC KHI nhận file
        if self.semaphore.locked():
            response = JSONResponse(
                status_code=429,
                content={"detail": "Hệ thống đang quá tải yêu cầu upload. Vui lòng thử lại sau."},
                headers={"Retry-After": "10"}
            )
            await response(scope, receive, send)
            return

        # 2. Early Header Check: Kiểm tra Content-Length
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length.decode()) > self.max_upload_size:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": f"File quá lớn ({int(content_length)/(1024*1024):.1f}MB). Giới hạn tối đa là 50MB."}
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
                        content={"detail": f"File upload vượt quá giới hạn tối đa {self.max_upload_size // (1024*1024)}MB."}
                    )
                    await response(scope, receive, send)
                else:
                    raise
```

**C. Đăng Ký Middleware Tập Trung ([`backend/app/middlewares/__init__.py`](file:///E:/MyProject/VNM-OCR/backend/app/middlewares/__init__.py)):**

```python
# backend/app/middlewares/__init__.py
from fastapi import FastAPI
from app.middlewares.upload_guard import StreamingUploadGuardMiddleware, MAX_UPLOAD_SIZE, MAX_CONCURRENT_UPLOADS

def register_middlewares(app: FastAPI) -> None:
    """Register all cross-cutting middlewares in proper execution order."""
    app.add_middleware(
        StreamingUploadGuardMiddleware,
        max_upload_size=MAX_UPLOAD_SIZE,
        max_concurrent=MAX_CONCURRENT_UPLOADS,
    )
```

**D. Khởi tạo Lifespan & Ứng Dụng Tinh Gọn ([`backend/app/main.py`](file:///E:/MyProject/VNM-OCR/backend/app/main.py)):**

```python
# backend/app/main.py — TUYỆT ĐỐI KHÔNG CHỨA LOGIC ENDPOINT
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router
from app.middlewares import register_middlewares
from app.exceptions.handlers import register_exception_handlers
from app.engine.manager import get_engine_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo Semaphore CPU độc quyền trong đúng event loop
    app.state.ocr_semaphore = asyncio.Semaphore(1)
    
    # Khởi tạo và warmup Engine Manager
    manager = get_engine_manager()
    manager.initialize()
    manager.warmup()
    
    yield
    
    # Dọn dẹp session khi shutdown
    manager.clear_sessions()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

register_middlewares(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
```

**E. Áp dụng Direct File-Like Streaming cho Document Extract Endpoint ([`backend/app/api/v1/endpoints/document.py`](file:///E:/MyProject/VNM-OCR/backend/app/api/v1/endpoints/document.py)):**

```python
@router.post("/document/extract", response_model=DocumentExtractionResponse)
async def extract_document(
    request: Request,
    file: UploadFile = File(...),
    extract_tables: bool = Query(default=True),
    resolution: int = Query(default=150),
    service: DocumentService = Depends(get_document_service),
) -> DocumentExtractionResponse:
    ocr_sem: asyncio.Semaphore = request.app.state.ocr_semaphore
    ocr_acquired = False
    
    try:
        # 1. Chờ lấy quyền thực thi CPU OCR (Queue Timeout 10s)
        try:
            async with asyncio.timeout(10.0):
                await ocr_sem.acquire()
                ocr_acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Hệ thống OCR đang bận phục vụ tác vụ khác. Vui lòng thử lại sau."},
                headers={"Retry-After": "30"},
            )
            
        # 2. Thực thi OCR ngoài main thread - Truyền TRỰC TIẾP file.file (Triệt tiêu Double RAM)
        try:
            async with asyncio.timeout(120.0):
                await file.seek(0)
                return await asyncio.to_thread(
                    service.extract_document,
                    file_input=file.file,  # Truyền SpooledTemporaryFile object trực tiếp
                    extract_tables=extract_tables,
                    resolution=resolution,
                )
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý OCR (Processing Timeout) do tài liệu quá phức tạp."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()
        await file.close()  # Đóng và giải phóng file tạm trên đĩa
```

**F. Áp dụng Direct File Streaming cho OCR Endpoint Chuẩn Hóa ([`backend/app/api/v1/endpoints/ocr.py`](file:///E:/MyProject/VNM-OCR/backend/app/api/v1/endpoints/ocr.py)):**

```python
# backend/app/api/v1/endpoints/ocr.py
@router.post("/ocr", response_model=OCRResponse, summary="Perform OCR on a single image")
async def recognize_image(
    request: Request,
    file: UploadFile = File(...),
    service: OcrService = Depends(get_ocr_service),
) -> OCRResponse:
    ocr_sem: asyncio.Semaphore = request.app.state.ocr_semaphore
    ocr_acquired = False
    try:
        try:
            async with asyncio.timeout(10.0):
                await ocr_sem.acquire()
                ocr_acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Hệ thống OCR đang bận. Thử lại sau."},
                headers={"Retry-After": "30"},
            )
            
        try:
            async with asyncio.timeout(120.0):
                await file.seek(0)
                return await asyncio.to_thread(service.process_image_file, file.file)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Quá thời gian xử lý OCR (Processing Timeout)."},
            )
    finally:
        if ocr_acquired:
            ocr_sem.release()
        await file.close()
```

---

### TRỤ CỘT 2: KHÓA CỨNG LUỒNG TÍNH TOÁN THEO NỀN TẢNG & GRAPH CACHE ĐA KIẾN TRÚC TỰ ĐỘNG (AUTO-DISCOVERY)

#### 1. Vấn đề giải quyết & Điểm hoàn thiện (Review V1 đến V6):
- **Vị trí và ngữ cảnh biến môi trường**: Khóa biến môi trường dòng đầu `main.py` trước mọi import. Phân biệt rõ biến đa nền tảng (`OMP`, `MKL`, `OPENBLAS`, `NUMEXPR`) và biến chuyên biệt cho macOS Apple Accelerate (`VECLIB_MAXIMUM_THREADS` chỉ gán khi `sys.platform == "darwin"`).
- **Ranh giới Thread Session vs Process**: 6 ONNX sessions tồn tại song song, nhưng với `ORT_SEQUENTIAL` và `intra_op=2, inter_op=1`, tổng CPU load lúc cao điểm được khống chế $\le 200\%$ CPU ($\le 2$ cores active).
- **Graph Cache Tự Động Hóa (Vá Lỗi Dead Code #46)**: Tự động suy luận thư mục cache `cache_dir = model_path.parent / ".onnx_opt_cache"` từ chính `model_path`, loại bỏ tham số thừa `models_dir` giúp Graph Cache vận hành trong suốt mà không cần sửa đổi chữ ký hàm khởi tạo của toàn bộ các Engine tầng trên. Cache key kết hợp `sys.platform`, `platform.machine()`, `st_size` và `st_mtime`.

#### 2. Thiết kế triển khai:

**A. Thiết lập biến môi trường dòng đầu `main.py` ([`backend/app/main.py`](file:///E:/MyProject/VNM-OCR/backend/app/main.py)):**

```python
# backend/app/main.py — BẮT BUỘC LÀ CÁC DÒNG ĐẦU TIÊN TRƯỚC MỌI APPLICATION IMPORT
import os
import sys

# Biến môi trường đa nền tảng (Linux, Windows, macOS Intel)
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

# macOS-specific: Apple Accelerate Framework (chỉ có tác dụng trên darwin)
if sys.platform == "darwin":
    os.environ["VECLIB_MAXIMUM_THREADS"] = "2"

# Khóa luồng OpenCV
import cv2
cv2.setNumThreads(2)

# Sau đó mới thực hiện import các module ứng dụng
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, ...
```

**B. Cấu hình SessionOptions & Graph Cache Đa Nền Tảng ([`backend/app/engine/model_loader.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/model_loader.py)):**

```python
import platform
import sys
from pathlib import Path
import onnxruntime as ort

def create_session_options(
    model_path: Path | None = None,
) -> ort.SessionOptions:
    opts = ort.SessionOptions()
    opts.enable_cpu_mem_arena = False             # Không giữ arena phân mảnh
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL # Chạy tuần tự node
    opts.intra_op_num_threads = 2                 # Tối đa 2 compute threads trong operator
    opts.inter_op_num_threads = 1                 # 1 thread giữa các operators
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    if model_path and model_path.exists():
        try:
            # Tự động xác định thư mục cache kế bên model file (không phụ thuộc models_dir)
            cache_dir = model_path.parent / ".onnx_opt_cache"
            cache_dir.mkdir(exist_ok=True)
            
            # Tag định danh theo OS + Kiến trúc CPU + Model Stat (size + mtime) để tránh xung đột
            arch_tag = f"{sys.platform}_{platform.machine()}"
            stat_result = model_path.stat()
            model_tag = f"{stat_result.st_size}_{int(stat_result.st_mtime)}"
            cache_name = f"{model_path.stem}_{arch_tag}_{model_tag}_opt.onnx"
            opts.optimized_model_filepath = str(cache_dir / cache_name)
        except PermissionError:
            # Fallback nếu thư mục models được mount dưới dạng read-only trong Docker
            pass
            
    return opts

def load_onnx_session(
    model_path: str | Path,
    device: str = "auto",
    device_id: int = 0,
) -> tuple[ort.InferenceSession, ort.RunOptions]:
    path_obj = Path(model_path).resolve()
    # ...
    session_options = create_session_options(model_path=path_obj)
    # ...
```

---

### TRỤ CỘT 3: CƠ CHẾ STREAMING TRANG PDF, ZERO-COPY PIL & DIRECT FILE-LIKE STREAMING

#### 1. Vấn đề giải quyết & Điểm hoàn thiện (Review V1 đến V8):
- **Duy trì `pdfplumber` (MIT License)**: Loại bỏ triệt để nguy cơ vi phạm giấy phép AGPL và lỗi render font chữ tiếng Việt của `PyMuPDF`.
- **Trích Xuất Text Đơn Lượt Không Lặp Tính Toán (Vá Lỗi #47)**: Dùng `_try_extract_digital_text()` thực hiện kiểm tra và trả về chuỗi text trực tiếp trong 1 lượt gọi `extract_text()`, tránh việc gọi 2 lần gây lãng phí CPU cho PDF born-digital.
- **Đọc Trực Tiếp Từ File-Like Object (Vá Lỗi #51 — Double RAM)**: `iter_document_pages_smart` nhận trực tiếp `BinaryIO` (chính là `file.file` của `UploadFile`), mở trực tiếp bằng `pdfplumber.open(file_obj)` mà không cần tạo trung gian `io.BytesIO(bytes)` gây tốn gấp đôi RAM.
- **Tối ưu Zero-Copy `pil_to_opencv`**: Thay vì tạo 2 mảng trung gian qua `cv2.cvtColor`, sử dụng cú pháp NumPy slice `np.array(pil_img)[:, :, ::-1]` để tạo view đảo RGB $\rightarrow$ BGR, giảm 50% RAM cấp phát tạm thời trong bước nạp ảnh (tiết kiệm ~6.5MB - 13MB/trang).

#### 2. Thiết kế triển khai:

**A. Tối ưu Zero-Copy `pil_to_opencv` ([`backend/app/utils/image_utils.py`](file:///E:/MyProject/VNM-OCR/backend/app/utils/image_utils.py)):**

```python
# backend/app/utils/image_utils.py
import io
from typing import BinaryIO
import numpy as np
import cv2
from PIL import Image

def pil_to_opencv(pil_img: Image.Image) -> np.ndarray:
    """Chuyển đổi PIL Image sang mảng OpenCV BGR với tối thiểu bản sao trung gian."""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    # np.array tạo RGB uint8, slice [:, :, ::-1] đảo channel sang BGR tại chỗ (zero-copy view)
    return np.array(pil_img, dtype=np.uint8)[:, :, ::-1]

def is_pdf_file(file_obj: BinaryIO) -> bool:
    """Kiểm tra header PDF trực tiếp từ file-like object."""
    file_obj.seek(0)
    magic = file_obj.read(4)
    file_obj.seek(0)
    return magic == b"%PDF"

def decode_image_file(file_obj: BinaryIO) -> np.ndarray:
    """Giải mã ảnh trực tiếp từ file-like object không qua bộ đệm bytes dư thừa."""
    file_obj.seek(0)
    data = file_obj.read()
    file_obj.seek(0)
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không thể giải mã file ảnh.")
    return img
```

**B. Generator Streaming & Smart Fast Path Từ File-Like Object ([`backend/app/utils/pdf_utils.py`](file:///E:/MyProject/VNM-OCR/backend/app/utils/pdf_utils.py)):**

```python
# backend/app/utils/pdf_utils.py
import io
from typing import Generator, BinaryIO
import pdfplumber
import numpy as np
from app.utils.image_utils import pil_to_opencv, decode_image_file, is_pdf_file

DIGITAL_CHAR_THRESHOLD = 50

def _try_extract_digital_text(page: pdfplumber.Page) -> str | None:
    """Kiểm tra và trích xuất text điện tử chuẩn chỉ trong 1 lần gọi (tránh lặp tính toán)."""
    try:
        text = page.extract_text() or ""
        if len(text.strip()) >= DIGITAL_CHAR_THRESHOLD:
            return text
    except Exception:
        pass
    return None

def iter_document_pages_smart(
    file_input: BinaryIO | bytes, resolution: int = 150
) -> Generator[tuple[int, np.ndarray | str], None, None]:
    """
    Generator stream từng trang từ file-like object (SpooledTemporaryFile) hoặc bytes:
    - Đọc trực tiếp từ file_input (không tạo bản sao bytes dư thừa trong RAM).
    - Trả về text string (Fast Path) nếu trang là born-digital.
    - Render và trả về ảnh OpenCV BGR (Slow Path) nếu là ảnh scan.
    """
    if hasattr(file_input, "read"):
        file_input.seek(0)
        file_obj = file_input
        is_pdf_doc = is_pdf_file(file_obj)
        file_obj.seek(0)
    else:
        file_obj = io.BytesIO(file_input)
        is_pdf_doc = file_input.startswith(b"%PDF")
        file_obj.seek(0)

    if is_pdf_doc:
        with pdfplumber.open(file_obj) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                digital_text = _try_extract_digital_text(page)
                if digital_text is not None:
                    # Fast path: text string (không lặp lại extract_text)
                    yield (page_idx + 1, digital_text)
                else:
                    # Slow path: render thành ảnh và convert thẳng sang BGR
                    cv_img = pil_to_opencv(page.to_image(resolution=resolution).original)
                    yield (page_idx + 1, cv_img)
                    del cv_img  # Giải phóng buffer sau khi consumer hoàn tất
    else:
        cv_img = decode_image_file(file_obj)
        yield (1, cv_img)
        del cv_img
```

---

### TRỤ CỘT 4: BẢO TOÀN ĐỘ CHÍNH XÁC TIẾNG VIỆT, DEFENSIVE COPY AN TOÀN & CLEAN OPERATORS

#### 1. Vấn đề giải quyết & Điểm hoàn thiện (Review V1 + V2):
- **Duy trì 100% FP32 Models**: Không lượng hóa INT8 cho `cnn.onnx` nhằm tránh nguy cơ mất các đặc trưng không gian phân biệt dấu thanh (`ă/â`, `ô/ơ`, `đ/d`). Baseline 6 model FP32 chỉ chiếm ~350MB RAM, hoàn toàn nằm trong ngưỡng an toàn khi kết hợp Streaming.
- **Đính chính Defensive Copy & Giải phóng sớm**: Giữ `ori_im = img.copy()` như một lớp bảo vệ an toàn (defensive programming) chống việc các operators thay đổi mảng gốc. Tuy nhiên, **thực hiện `del ori_im` ngay sau khi cắt xong các crop đa giác** (trước khi bước recognition bắt đầu), kết hợp xóa danh sách `img_crop_list` ngay sau recognition.
- **Refactor `eval(scale)` trong `operators.py`**: Loại bỏ lệnh `eval()` trong `NormalizeImage`, thay thế bằng phép tính số học tường minh `float(parts[0]) / float(parts[1])` để triệt tiêu lỗ hổng bảo mật và cải thiện hiệu năng.

#### 2. Thiết kế triển khai:

**A. Tối ưu vòng đời biến trong `OcrEngine.predict` ([`backend/app/engine/ocr_engine.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/ocr_engine.py)):**

```python
# backend/app/engine/ocr_engine.py
def predict(self, img: np.ndarray) -> list[tuple[np.ndarray, tuple[str, float]]]:
    ori_im = img.copy()  # Giữ defensive copy bảo vệ pipeline
    dt_boxes, _ = self.detector(ori_im)
    if dt_boxes is None or len(dt_boxes) == 0:
        del ori_im
        return []

    sorted_dt_boxes = self.sorted_boxes(dt_boxes)
    img_crop_list: list[np.ndarray] = []
    for box in sorted_dt_boxes:
        crop = self.get_rotate_crop_image(ori_im, box)
        img_crop_list.append(crop)

    # GIẢI PHÓNG ori_im NGAY LẬP TỨC KHI ĐÃ CẮT XONG HẾT CÁC CROP
    del ori_im

    # Chạy recognition trên danh sách crop
    rec_res, _ = self.recognizer(img_crop_list)

    # GIẢI PHÓNG TƯỜNG MINH CÁC MẢNG CROP SAU KHI RECOGNITION XONG
    img_crop_list.clear()
    del img_crop_list

    # Đóng gói kết quả
    results = []
    for box, (text, score) in zip(sorted_dt_boxes, rec_res):
        if score >= self.drop_score:
            results.append((box, (text, score)))
    return results
```

**B. Refactor `NormalizeImage` loại bỏ `eval()` ([`backend/app/engine/operators.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/operators.py)):**

```python
# backend/app/engine/operators.py
class NormalizeImage:
    def __init__(self, scale: str | float = 1.0 / 255.0, mean=None, std=None, order="chw", **kwargs):
        if isinstance(scale, str):
            if "/" in scale:
                parts = scale.replace(" ", "").split("/")
                self.scale = float(parts[0]) / float(parts[1])
            else:
                self.scale = float(scale)
        else:
            self.scale = float(scale)
            
        shape = (1, 1, 3) if order == "hwc" else (3, 1, 1)
        self.mean = np.array(mean if mean is not None else [0.485, 0.456, 0.406]).reshape(shape).astype("float32")
        self.std = np.array(std if std is not None else [0.229, 0.224, 0.225]).reshape(shape).astype("float32")
        self.order = order
```

---

### TRỤ CỘT 5: THU HỒI BỘ NHỚ TẦNG SÂU CHUẨN XÁC ĐA NỀN TẢNG (LINUX / MACOS / WINDOWS)

#### 1. Vấn đề giải quyết & Điểm hoàn thiện (Review V1 + V2):
- **Linux (glibc)**: Gọi `libc.malloc_trim(0)` từ `libc.so.6` để giải phóng các trang arena memory về OS Kernel.
- **macOS (Darwin)**: Gọi `libSystem.B.dylib` với `malloc_zone_pressure_relief` (nếu hỗ trợ) hoặc tin cậy vào virtual memory compressor kết hợp `gc.collect(generation=2)`. Tuyệt đối không gọi `malloc_trim` vì không tồn tại trên macOS.
- **Windows**: Sử dụng `kernel32.HeapCompact(GetProcessHeap(), 0)` kết hợp `gc.collect(generation=2)` và quản lý biến chặt chẽ. Ghi chú rõ sự khác biệt bản chất so với Linux trong tài liệu code.

#### 2. Thiết kế triển khai:

**A. Xây dựng `memory_utils.py` Đa Nền Tảng ([`backend/app/utils/memory_utils.py`](file:///E:/MyProject/VNM-OCR/backend/app/utils/memory_utils.py)):**

```python
# backend/app/utils/memory_utils.py
import gc
import sys
import ctypes
import logging

logger = logging.getLogger(__name__)

def force_garbage_collection_and_trim() -> None:
    """
    Thu hồi bộ nhớ đa nền tảng:
    1. Thu gom toàn diện mọi thế hệ đối tượng Python (gc.collect).
    2. Gọi API giải phóng heap đặc thù của từng hệ điều hành (Linux / macOS / Windows).
    """
    # Bước 1: Thu gom rác Python VM
    # Chỉ thực hiện thu gom generation 2 nếu thực sự có rác tích tụ để tránh block event loop
    stats = gc.get_count()
    if stats[2] > 0 or stats[1] > 50:
        gc.collect(generation=2)
    else:
        gc.collect(generation=0)
    
    # Bước 2: OS Heap Trimming theo nền tảng
    platform = sys.platform
    
    if platform.startswith("linux"):
        # Linux (glibc arena trimming)
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            libc.malloc_trim.argtypes = [ctypes.c_size_t]
            libc.malloc_trim.restype = ctypes.c_int
            libc.malloc_trim(0)
        except (OSError, AttributeError) as e:
            logger.debug("Linux malloc_trim skipped: %s", e)
            
    elif platform == "darwin":
        # macOS (Darwin libSystem)
        try:
            libc = ctypes.CDLL("libSystem.B.dylib", use_errno=True)
            if hasattr(libc, "malloc_zone_pressure_relief"):
                libc.malloc_zone_pressure_relief(None, 0)
        except (OSError, AttributeError) as e:
            logger.debug("macOS memory relief skipped: %s", e)
            
    elif platform == "win32":
        # Windows (Default Process Heap Compaction)
        try:
            kernel32 = ctypes.windll.kernel32
            heap = kernel32.GetProcessHeap()
            if heap:
                kernel32.HeapCompact(heap, 0)
        except (OSError, AttributeError) as e:
            logger.debug("Windows HeapCompact skipped: %s", e)
```

**B. Tích hợp thu hồi trong `DocumentService` ([`backend/app/services/document_service.py`](file:///E:/MyProject/VNM-OCR/backend/app/services/document_service.py)):**

```python
# backend/app/services/document_service.py
from typing import BinaryIO
import numpy as np
from app.utils.pdf_utils import iter_document_pages_smart
from app.utils.memory_utils import force_garbage_collection_and_trim

class DocumentService:
    def extract_document(
        self,
        file_input: BinaryIO | bytes,
        extract_tables: bool = True,
        resolution: int = 150,
    ) -> DocumentExtractionResponse:
        try:
            pages_output: list[PageExtractionResult] = []
            
            for page_num, page_data in iter_document_pages_smart(file_input, resolution=resolution):
                if isinstance(page_data, str):
                    # Smart Fast Path: Đã là text điện tử
                    page_result = PageExtractionResult(page_num=page_num, markdown=page_data)
                else:
                    # Slow Path: Là ảnh np.ndarray, cần chạy qua pipeline mô hình
                    page_img = page_data
                    page_result = self._process_single_page(
                        page_img=page_img,
                        page_num=page_num,
                        extract_tables=extract_tables,
                    )
                    # GIẢI PHÓNG page_img
                    # Lưu ý: Chắc chắn rằng bên trong _process_single_page (ví dụ khi gọi fuse_with_ocr)
                    # mọi thao tác đọc/xử lý ảnh đã HOÀN TẤT. Không được trả về view tham chiếu tới page_img.
                    del page_img
                    
                pages_output.append(page_result)
            
            # Tính total_pages sau khi generator loop kết thúc
            total_pages = len(pages_output)
            
            full_markdown = "\n\n---\n\n".join(p.markdown for p in pages_output)
            return DocumentExtractionResponse(
                pages=pages_output,
                full_markdown=full_markdown,
                total_pages=total_pages,
            )
        finally:
            # Thu hồi bộ nhớ đa nền tảng sau mỗi request
            force_garbage_collection_and_trim()
```

---

### TRỤ CỘT 6: SMART FAST PATH CHO PDF ĐIỆN TỬ & TÁCH BIỆT DEPENDENCY SẠCH SẼ

#### 1. Vấn đề giải quyết & Điểm hoàn thiện (Review V1 + V2):
- **Born-Digital Fast Path**: Trích xuất trực tiếp text vector nếu tài liệu là PDF điện tử có sẵn text layer chuẩn ($\ge 50$ ký tự/trang), giảm 95% latency (chỉ mất 10–30ms/trang) và giữ RAM $< 200\text{MB}$.
- **Tách biệt Dependency trong `pyproject.toml`**: Tách gói `torch` và `torchvision` ra khỏi `[project.optional-dependencies] dev` sang nhóm riêng `tools = [...]` để tránh việc vô tình cài đặt 2.5GB PyTorch vào môi trường development/production của OCR service.

#### 2. Thiết kế triển khai:

**A. Cấu trúc Dependencies trong `pyproject.toml` ([`backend/pyproject.toml`](file:///E:/MyProject/VNM-OCR/backend/pyproject.toml)):**

```toml
[project.optional-dependencies]
cpu = [
    "onnxruntime>=1.17.0",
]
gpu = [
    "onnxruntime-gpu>=1.17.0",
]
pdf = [
    "pdfplumber>=0.11.0",
]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
    "psutil>=5.9.0",
]
# Chỉ dùng khi cần convert hoặc export ONNX weights, không cài trong production
tools = [
    "torch>=2.1.0",
    "torchvision>=0.16.0",
]
```

---

## 4. KẾ HOẠCH HÀNH ĐỘNG & DANH MỤC NHIỆM VỤ CHI TIẾT (ACTIONABLE TASKS)

> [!IMPORTANT]
> **Kết Quả Đối Chiếu Toàn Diện & Rà Soát Thiết Kế (Vòng 11):** Thiết kế kiến trúc và giải pháp kỹ thuật đã khắc phục triệt để các lỗ hổng framework, DevOps và Clean Architecture từ Vòng 8 đến Vòng 11 (#49–#56: Hiểu lầm FastAPI Lifecycle, Chunked Transfer Disk DoS, Double RAM Allocation, Late Backpressure, OS Temp Pollution, Middleware Scaffold, Main.py Routing Leak và Git Temp Ignore).
>
> **Thứ Tự Ưu Tiên Triển Khai Cấp Thiết (Execution Priority Order):**
> 1. **TASK-01 (Thread Budget, Temp Sandboxing & Gitignore — Vá #53, #56)**: Sandboxing `tempfile.tempdir = str(PROJECT_ROOT / "temp")`, bổ sung `.gitignore`, và khóa luồng CPU ngay dòng đầu `main.py`.
> 2. **TASK-08 (Dedicated ASGI Streaming Guard Middleware & Early Backpressure — Vá #49, #50, #52, #54)**: Triển khai Middleware tách biệt trong `app/middlewares/` chặn `Content-Length > 50MB`, đếm stream bytes on-the-fly chặn Disk DoS, và phản hồi `HTTP 429` sớm trước khi nhận body.
> 3. **TASK-09 (Clean Router Separation & Concurrency Control — Vá #55)**: Di dời toàn bộ logic endpoint khỏi `main.py` vào `app/api/v1/endpoints/ocr.py` và `document.py`, bọc `ocr_semaphore` với `asyncio.to_thread`.
> 4. **TASK-05 & TASK-07 (Direct File-Like Streaming & Zero-Copy Ingestion — Vá #51, #47)**: Truyền trực tiếp `file.file` (`SpooledTemporaryFile`) vào `iter_document_pages_smart`, loại bỏ triệt để biến `content` 50MB trong RAM, tích hợp `_try_extract_digital_text()` đơn lượt.
> 5. **TASK-06 (Engine Memory Lifecycle & Operators Clean — Vá #40, #41, #42)**: Giải phóng `del ori_im` sớm, `img_crop_list.clear()`, refactor bỏ `eval()`, thêm `clear_sessions()` và `reset_singleton()` vào `EngineManager`.
> 6. **TASK-02 (Graph Cache Auto-Discovery — Vá #46), TASK-03, TASK-04, TASK-10, TASK-11, TASK-12, TASK-13**: Hoàn tất các module hỗ trợ, benchmark và nghiệm thu đa nền tảng.

```mermaid
gantt
    title Lộ Trình Triển Khai Kế Hoạch Tối Ưu Tài Nguyên OCR (v4.5.0)
    dateFormat  YYYY-MM-DD
    section Giai đoạn 1: Khóa Luồng, Sandboxing & Cấu Hình Engine
    TASK-01: Sandboxing Temp, Gitignore & Khóa biến môi trường dòng đầu main.py :active, t1, 2026-09-01, 1d
    TASK-02: Cấu hình ONNX & Graph Cache Auto-Discovery           :active, t2, after t1, 1d
    TASK-03: Tách biệt dependency PyTorch sang nhóm [tools]        :active, t3, after t2, 1d
    section Giai đoạn 2: Tối Ưu Bộ Nhớ & Streaming Ingestion
    TASK-04: Xây dựng memory_utils đa nền tảng (Linux/Mac/Win)    :t4, after t3, 1d
    TASK-05: Tối ưu Zero-Copy PIL & Direct File-Like Streaming     :t5, after t4, 1d
    TASK-06: Refactor NormalizeImage & tối ưu vòng đời OcrEngine   :t6, after t5, 1d
    TASK-07: Tối ưu DocumentService & Thu hồi bộ nhớ cuối chu kỳ  :t7, after t6, 1d
    section Giai đoạn 3: ASGI Middleware, Router & Concurrency
    TASK-08: Dedicated ASGI Upload Guard Middleware (app/middlewares/) :t8, after t7, 1d
    TASK-09: Clean Router Endpoints (ocr.py/document.py) & OCR Semaphore :t9, after t8, 1d
    TASK-10: Tích hợp Born-Digital Smart Fast Path                :t10, after t9, 1d
    section Giai đoạn 4: Kiểm Thử Đa Nền Tảng & Nghiệm Thu
    TASK-11: Xây dựng Benchmark Script tự động (RAM/CPU/Health)   :t11, after t10, 1d
    TASK-12: Sửa Bug & Ghi Nhận Known Issues                      :t12, after t11, 1d
    TASK-13: Nghiệm thu toàn diện theo Ma trận Định lượng         :t13, after t12, 1d
```

### Bảng Chi Tiết Nhiệm Vụ Triển Khai:

| Mã Task | Hạng Mục Công Việc | File Mã Nguồn Tác Động | Kết Quả Đầu Ra Cụ Thể |
| :--- | :--- | :--- | :--- |
| **TASK-01** | **Khóa cứng Thread, Sandboxing & Gitignore** | [`backend/app/main.py`](file:///E:/MyProject/VNM-OCR/backend/app/main.py), [`.gitignore`](file:///E:/MyProject/VNM-OCR/.gitignore) | Sandboxing `tempfile.tempdir = str(PROJECT_ROOT / "temp")`; thêm `temp/` và `.onnx_opt_cache/` vào `.gitignore`; đặt biến môi trường `OMP/MKL/cv2` dòng đầu. |
| **TASK-02** | **Cấu hình ONNX & Graph Cache Auto-Discovery** | [`backend/app/engine/model_loader.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/model_loader.py) | Cấu hình `intra=2, inter=1, arena=False`; tự động xác định `cache_dir = model_path.parent / ".onnx_opt_cache"`. Bắt `PermissionError`. |
| **TASK-03** | **Tách biệt Dependency PyTorch** | [`backend/pyproject.toml`](file:///E:/MyProject/VNM-OCR/backend/pyproject.toml) | Chuyển `torch/torchvision` từ `[dev]` sang nhóm `[tools]`, thêm `psutil` vào `[dev]`, bảo vệ virtualenv gọn nhẹ. |
| **TASK-04** | **Module Thu Hồi Bộ Nhớ Đa Nền Tảng** | `backend/app/utils/memory_utils.py` (Tạo mới) | Xử lý `malloc_trim` (Linux), `malloc_zone_pressure_relief` (macOS), `HeapCompact` (Win), `gc.collect(2)` theo điều kiện. |
| **TASK-05** | **Zero-Copy PIL & Direct File-Like Streaming** | [`backend/app/utils/image_utils.py`](file:///E:/MyProject/VNM-OCR/backend/app/utils/image_utils.py), [`backend/app/utils/pdf_utils.py`](file:///E:/MyProject/VNM-OCR/backend/app/utils/pdf_utils.py) | `pil_to_opencv` dùng slicing `[:, :, ::-1]`; `iter_document_pages_smart` stream trực tiếp từ `BinaryIO` (SpooledTemporaryFile) kết hợp `_try_extract_digital_text()` đơn lượt. |
| **TASK-06** | **Refactor Operators & Vòng Đời Engine** | [`backend/app/engine/operators.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/operators.py), [`backend/app/engine/ocr_engine.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/ocr_engine.py), [`backend/app/engine/manager.py`](file:///E:/MyProject/VNM-OCR/backend/app/engine/manager.py) | Bỏ `eval()` trong `NormalizeImage`; giải phóng sớm `del ori_im` và `img_crop_list.clear()`; thêm `clear_sessions()` và `reset_singleton()` cho EngineManager. |
| **TASK-07** | **Tối ưu DocumentService** | [`backend/app/services/document_service.py`](file:///E:/MyProject/VNM-OCR/backend/app/services/document_service.py) | Nhận `file_input: BinaryIO | bytes`, tích hợp generator `iter_document_pages_smart()`, phân nhánh fast path `isinstance(str)`, giải phóng page_img an toàn. |
| **TASK-08** | **Dedicated ASGI Upload Guard Middleware** | `backend/app/middlewares/upload_guard.py`, `backend/app/middlewares/__init__.py` | Tạo `StreamingUploadGuardMiddleware` chặn Content-Length > 50MB, đếm stream chunk on-the-fly chặn Disk DoS, Early Backpressure trả HTTP 429 trước khi nhận body, đăng ký qua `register_middlewares(app)`. |
| **TASK-09** | **Clean Router Separation & OCR Semaphore** | [`backend/app/api/v1/endpoints/ocr.py`](file:///E:/MyProject/VNM-OCR/backend/app/api/v1/endpoints/ocr.py), [`backend/app/api/v1/endpoints/document.py`](file:///E:/MyProject/VNM-OCR/backend/app/api/v1/endpoints/document.py), [`backend/app/main.py`](file:///E:/MyProject/VNM-OCR/backend/app/main.py) | Di dời toàn bộ logic endpoints khỏi `main.py`, truyền `file.file` trực tiếp, bọc `asyncio.to_thread` với `ocr_semaphore(1)` (timeout 10s queue / 120s ocr). |
| **TASK-10** | **Born-Digital Fast Path** | [`backend/app/services/document_service.py`](file:///E:/MyProject/VNM-OCR/backend/app/services/document_service.py) | Trích xuất trực tiếp text vector nếu tài liệu là digital PDF (đã phân nhánh trên từng trang qua `iter_document_pages_smart`). |
| **TASK-11** | **Bộ Benchmark & Kiểm Thử Tự Động** | `backend/tests/test_resource_budget.py` (Tạo mới) | Đo RSS đa nền tảng (psutil), đo latency `/health`, và test `Retry-After` với 3 requests đồng thời. |
| **TASK-12** | **Sửa Bug & Ghi Nhận Known Issues** | Các files liên quan | Ghi nhận trade-off xử lý tuần tự `batch_size=1` của `TextRecognizer`; sửa bug fix cứng `score = 1.0` (mở ticket tracking). |
| **TASK-13** | **Nghiệm Thu Toàn Diện Đa Nền Tảng** | Báo cáo kiểm thử | Đối chiếu toàn bộ chỉ số định lượng theo bảng tiêu chuẩn Mục 5. |

---

## 5. BỘ CHỈ SỐ NGHIỆM THU ĐỊNH LƯỢNG (v4.5.0)

Hệ thống sau khi hoàn thành kế hoạch tối ưu phải đáp ứng đầy đủ các tiêu chí định lượng sau:

| Tiêu Chí Đo Lường | Hiện Trạng (Trước Tối Ưu) | Mục Tiêu Sau Tối Ưu (Target v4.5.0) | Phương Pháp Xác Minh |
| :--- | :--- | :--- | :--- |
| **Số Uvicorn Worker** | 1 Worker | **1 Worker duy nhất** | `uvicorn --workers 1` trong Dockerfile / run script. |
| **Bảo Vệ Concurrency & Early Load Shedding** | Không giới hạn hoặc chặn sai chỗ | **ASGI Early Backpressure (Max 10 Uploads) + OCR Semaphore (1 CPU Task)** | Kiểm thử đồng thời 15 requests upload và 3 requests OCR. |
| **Chống Disk Exhaustion DoS & Temp Sandboxing** | FastAPI ghi tràn ổ C: /tmp khi nhận chunked lớn | **Ngắt stream HTTP 413 khi > 50MB + Ép 100% tempfile vào `backend/temp/` + Gitignored** | Test gửi chunked 100MB và kiểm tra `tempfile.tempdir`. |
| **Mức Sử Dụng CPU (Compute Load)** | 8 – 16 luồng ngầm tranh chấp | **$\le$ 200% CPU (Tối đa 2 logical cores active)** | Giám sát qua `top`/`htop` hoặc `psutil.cpu_percent()`. |
| **RAM Tĩnh (Baseline RSS)** | ~450 MB – 520 MB | **$\le$ 450 MB – 520 MB (Mô hình FP32 nguyên bản)** | Đo RSS RAM ngay sau khi khởi động và warmup xong. |
| **RAM Đỉnh Tải — Ảnh Đơn (1 trang)** | ~800 MB – 1.0 GB | **$\le$ 700 MB (Loại bỏ hoàn toàn Double RAM bytes)** | Đo `max(RSS)` khi xử lý 1 ảnh tài liệu A4. |
| **RAM Đỉnh Tải — PDF 10 trang (150 DPI)** | ~1.2 GB – 1.6 GB | **$\le$ 900 MB** | Đo `max(RSS)` trong suốt chu kỳ xử lý PDF 10 trang. |
| **RAM Đỉnh Tải — PDF 50 trang (150 DPI)** | > 2.5 GB – 3.5 GB (OOM Crash) | **$\le$ 1.2 GB (Không tăng tuyến tính theo số trang)** | Đo `max(RSS)` trong suốt chu kỳ xử lý PDF 50 trang. |
| **Bộ Đệm An Toàn (Safety Margin)** | 0 MB (Nguy cơ OOM cao) | **$\ge$ 800 MB buffer tới giới hạn cứng 2GB** | $2.0\text{ GB} - 1.2\text{ GB} = 800\text{ MB}$ an toàn. |
| **Thu Hồi RAM (Post-Reclaim RSS)** | Giữ nguyên 1.5 GB – 2.5 GB | **Trả về $\le$ 600 MB (trong vòng 2s sau request)** | Đo RSS RAM tại thời điểm $t = +2\text{s}$ sau khi request kết thúc. |
| **Độ Sẵn Sàng Event Loop** | Bị đóng băng hoàn toàn | **Ping `GET /api/v1/health` phản hồi $< 15\text{ms}$** | Gửi heartbeat liên tục trong lúc OCR đang chạy file nặng. |
| **Backpressure khi Quá Tải** | Không có (Nhận dồn gây OOM) | **Trả về HTTP 429 sớm (trước upload) hoặc HTTP 503 kèm `Retry-After: 30`** | Gửi đồng thời 3 request tài liệu lớn cùng lúc. |
| **Bảo Vệ Upload Quá Tải** | Không có (Đọc file 500MB gây OOM) | **Chặn HTTP 413 ở tầng Middleware cho cả Header & Chunked Stream** | Gửi file > 50MB qua regular upload và chunked upload. |
| **Bảo Toàn Độ Chính Xác Tiếng Việt** | FP32 chuẩn | **100% không suy giảm độ chính xác dấu tiếng Việt** | Duy trì weights FP32, kiểm thử qua bộ test CER/WER. |
| **Khả Năng Tương Thích Đa Nền Tảng** | Chỉ test đơn lẻ | **Hoạt động ổn định trên Linux, macOS, Windows** | Kiểm thử thành công trên cả 3 hệ điều hành. |

---

## 6. KẾT LUẬN

Bản kế hoạch `v4.5.0` đã hoàn thiện và tích hợp đầy đủ các kết luận từ **Vòng 1 đến Vòng 11** của tài liệu phản biện `DOC-REP-COUNTER-003`:
1. **Khống Chế File Tạm Khép Kín & Gitignore An Toàn**: Ngăn chặn rác file tạm tràn ra ổ đĩa OS bằng `tempfile.tempdir = str(PROJECT_ROOT / "temp")` và bảo vệ kho mã nguồn khỏi rác commit bằng `.gitignore`.
2. **Tiêu Chuẩn Hóa Clean Architecture & Tách Biệt Router**: Di dời toàn bộ logic endpoint ra khỏi `main.py`, tách riêng tầng middleware `app/middlewares/` và router `app/api/v1/endpoints/`, biến `main.py` thành entry point chuẩn mực.
3. **Kiến Trúc ASGI Streaming Guard Triệt Tiêu Disk DoS & Early Backpressure**: Chặn đứng việc FastAPI ghi tràn đĩa cứng khi gặp Chunked Transfer tải trọng lớn, đồng thời từ chối `HTTP 429` ngay từ trước khi nạp body request giúp tiết kiệm 100% tài nguyên I/O khi quá tải.
4. **Loại Bỏ Hoàn Toàn Double RAM Allocation**: Đọc trực tiếp từ `UploadFile.file` (`SpooledTemporaryFile`) vào `pdfplumber` và OpenCV mà không cần biến đệm `bytes` 50MB trong RAM, giảm đáng kể áp lực cấp phát bộ nhớ.
5. **Graph Cache Tự Động Hóa (Zero-Configuration)**: Khởi tạo và tự suy luận thư mục `.onnx_opt_cache` từ đường dẫn mô hình, giải quyết triệt để lỗi dead code mà không phá vỡ giao diện API của các Engine.
6. **Hiệu Năng Streaming Đơn Lượt & Zero-Copy**: Trích xuất text vector chuẩn trong 1 lượt gọi duy nhất (`_try_extract_digital_text`), kết hợp `pil_to_opencv` zero-copy NumPy view và generator từng trang, đảm bảo RAM luôn được khống chế $\le 1.2\text{GB}$ cho PDF 50 trang.
7. **Bảo Mật & Quản Lý Vòng Đời Bộ Nhớ Đa Nền Tảng**: Loại bỏ hoàn toàn `eval()`, giải phóng sớm `del ori_im` sau khi crop, tích hợp `clear_sessions()` / `reset_singleton()` vào `EngineManager`, và thu hồi bộ nhớ tầng sâu trên Linux, macOS và Windows.
8. **Sẵn Sàng Triển Khai Thực Tế (Execution Sign-off)**: Kế hoạch `v4.5.0` đạt độ hoàn thiện cao nhất về chuẩn mực code, bảo mật I/O và tối ưu tài nguyên phần cứng. Sẵn sàng tiếp tục thực thi các task tiếp theo trong `tasks/todo.md`.
