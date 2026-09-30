# Software Requirements Specification (SRS) - Release 1

## 1. Giới thiệu
Tài liệu này đặc tả các yêu cầu phần mềm chi tiết cho VNM-OCR Release 1, tập trung vào kiến trúc phân luồng, kiểm soát tài nguyên phần cứng, và logic bóc tách tài liệu thông minh. Hệ thống được thiết kế ưu tiên chạy trên **laptop CPU-only 16GB RAM** với ngân sách bộ nhớ phân tầng.

Tài liệu nguồn kiến trúc Extractor: [`docs/research/smart_pdf_classification_and_hybrid_extraction.md`](file:///E:/MyProject/VNM-OCR/docs/research/smart_pdf_classification_and_hybrid_extraction.md) (v2.5.0).

## 2. Đặc tả Tính năng Backend & API

### 2.1. Quản lý Vòng đời & Tải trễ (Lazy Loading)
- **Cơ chế nạp Model:** ONNX Sessions không được nạp toàn bộ lúc khởi động (startup). Khởi tạo `EngineManager` dạng Singleton. Các engine (`OcrEngine`, `LayoutEngine`, `TableEngine`) chỉ nạp trọng số tương ứng khi có request API đầu tiên chạm vào endpoint cần dùng nó.
- **Hardware Matrix Detection:** Khởi chạy `get_available_providers()`. Tự động ưu tiên: `CUDAExecutionProvider` $\rightarrow$ `CoreMLExecutionProvider` $\rightarrow$ `CPUExecutionProvider`.
- **Import-on-Demand cho Optional Extractors:** `DoclingUniversalExtractor` và `PaddleOCRExtractor` sử dụng `importlib` để kiểm tra sự tồn tại của thư viện. Nếu không có → HTTP 501 Not Implemented kèm hướng dẫn cài đặt.
- **Giải phóng RAM (Reclaim):**
  - Đảm bảo thực thi `utils.memory_utils.force_garbage_collection_and_trim()` sau mỗi tác vụ xử lý ảnh hoặc PDF để trả tài nguyên cho OS ngay lập tức.

### 2.2. Memory Budget Monitor (Giám sát Ngân sách Bộ nhớ)
- **Mô tả:** Cơ chế giám sát chủ động RSS (Resident Set Size) của process, đảm bảo ứng dụng không bao giờ tiêu thụ quá ngưỡng RAM cho phép trên phần cứng mục tiêu.
- **Cấu hình ngưỡng (Configurable Thresholds):**
  - `MEMORY_SOFT_LIMIT`: Ngưỡng mềm, mặc định $2.0GB$ (Tier 1). Khi vượt: log warning, kích hoạt GC tích cực.
  - `MEMORY_HARD_LIMIT`: Ngưỡng cứng, mặc định $3.5GB$ (Tier 2 safety margin). Khi vượt: từ chối request mới (HTTP 503), **không cho phép nạp thêm model VLM**.
  - `MEMORY_CRITICAL_LIMIT`: Ngưỡng nguy hiểm, mặc định $\le 90\%$ tổng RAM hệ thống. Khi tiệm cận: emergency unload model ít dùng nhất, force GC generation=2.
- **Tích hợp:** Kiểm tra RSS tại 2 thời điểm:
  1. **Trước khi accept request** (trong Middleware hoặc Semaphore acquire).
  2. **Sau mỗi page processing** (trong vòng lặp generator `iter_document_pages_smart`).
- **Thư viện:** Sử dụng `psutil.Process().memory_info().rss` (cross-platform).

### 2.3. Smart PDF Inspector (v2.5.0) & Hybrid Dispatcher
- **Mô tả:** Mô-đun phân tích cú pháp PDF nội tại với 10 PageType chi tiết và phân luồng ngôn ngữ tường minh.
- **PageType Enum (Đồng bộ research v2.5.0):**

| PageType | Mô tả | Engine đích | `requires_image_input` | `is_vector_recovery` |
|----------|-------|-------------|----------------------|---------------------|
| `BORN_DIGITAL` | PDF sinh số, text stream sạch | NativePDFExtractor | False | False |
| `SCANNED` | PDF quét / ảnh chụp | VNMOCRExtractor / PaddleOCR | True | False |
| `GHOST_OCR` | Lớp OCR ẩn rác, text mất dấu | VNMOCRExtractor | True | True |
| `CORRUPTED_VECTOR_VI` | Font CMap vỡ, tiếng Việt | VNMOCRExtractor | True | True |
| `CORRUPTED_VECTOR_EN` | Font CMap vỡ, tiếng Anh | PaddleOCRExtractor | True | True |
| `COMPLEX_STRUCTURE_VI` | Bảng lồng / báo cáo tiếng Việt | VNMOCRExtractor | True | False |
| `COMPLEX_STRUCTURE_EN` | Paper khoa học, LaTeX Math | PaddleOCRExtractor (VL) | True | False |
| `MIXED` | Trang lai ảnh và chữ | VNMOCRExtractor / PaddleOCR | True | False |
| `IMAGE_ONLY` | Trang chỉ chứa ảnh | VNMOCRExtractor | True | False |
| `EMPTY` | Trang rỗng | Không áp dụng | False | False |

- **Quy trình phân loại:**
  1. Sample max 3 trang (đầu, giữa, cuối) từ tài liệu PDF.
  2. Với mỗi trang: phân tích text fraction, raster image count, PUA characters, math Unicode, bảng biểu.
  3. Tính SCS (Scanned Content Score) qua Multi-Signal Gating.
  4. Nhận diện ngôn ngữ: Vietnamese Syllable Fingerprint (regex dấu tiếng Việt) → phân luồng `_VI` / `_EN`.
  5. Aggregate profiles → Overall document classification.

- **UniversalDispatcher Routing (Strategy Pattern):**
  - `BORN_DIGITAL` (no complex): → `NativePDFExtractor` (Fast Path, pdfplumber trích text trực tiếp, $< 15ms$/trang).
  - `SCANNED`, `CORRUPTED_VECTOR_VI`, `GHOST_OCR`, `COMPLEX_STRUCTURE_VI`, `MIXED`: → `VNMOCRExtractor` (Heavy Pipeline: Render ảnh → DLA → OCR → TSR → Markdown).
  - `CORRUPTED_VECTOR_EN`, `COMPLEX_STRUCTURE_EN`: → `PaddleOCRExtractor` (PP-OCRv6 / PaddleOCR-VL).
  - Office formats (.docx, .xlsx, .pptx, html): → `DoclingUniversalExtractor`.

### 2.4. Endpoints Chuyên biệt (Explicit Dedicated Endpoints)
Hệ thống cung cấp danh sách Endpoints theo kiến trúc Explicit Dedicated Endpoints:

**Endpoints kế thừa (Phase 1-5, đang hoạt động):**
- `GET /api/v1/health`: Health check kèm thông tin RAM usage (`rss_mb`, `memory_budget_status`).
- `POST /api/v1/ocr`: Nhận diện text từ ảnh đơn (OCR only).
- `POST /api/v1/layout`: Trả về Bounding Box cấu trúc (DLA only).
- `POST /api/v1/table`: Trích xuất HTML/Markdown bảng biểu (TSR only).
- `POST /api/v1/document/extract`: Pipeline RAG chính, xử lý PDF/Image đầy đủ.
- `POST /api/ocr`: Adapter tương thích ngược cho Web UI.

**Endpoints mới Phase 6 (Comprehensive Extractors):**
- `POST /api/v1/extract/auto`: Router tự động, gọi SmartPDFInspector phân loại rồi dispatch đến Extractor phù hợp.
- `POST /api/v1/extract/native/pdf`: Explicit cho Digital PDF (NativePDFExtractor).
- `POST /api/v1/extract/vnm`: Explicit cho pipeline tiếng Việt (VNMOCRExtractor).
- `POST /api/v1/extract/docling`: Explicit cho xử lý Office (DoclingUniversalExtractor).
- `POST /api/v1/extract/paddle/ocr`: Explicit cho tiếng Anh chuẩn (PaddleOCRExtractor, PP-OCRv6).
- `POST /api/v1/extract/paddle/complex-vlm`: Explicit cho Paper/Math (PaddleOCRExtractor, PaddleOCR-VL).

### 2.5. Kiến trúc Extensible cho VLM (Future-Ready)
- **Interface `BaseRecognizer`:** Định nghĩa contract chung cho cả ONNX Recognizer và VLM Recognizer, cho phép swap runtime.
- **Config-driven Selection:** Chọn recognizer backend qua biến môi trường `OCR_RECOGNIZER_BACKEND=onnx|vlm` (mặc định `onnx`).
- **VLM Loading Guard:** Trước khi nạp VLM model, kiểm tra `available_ram = total_ram - current_rss`. Nếu `available_ram < VLM_MIN_RAM_REQUIRED` (mặc định 3GB), từ chối nạp và fallback về ONNX.

### 2.6. Comprehensive Format Extractors — Interface Contract
- **BaseExtractor (ABC):** Phương thức `extract(file_input: BinaryIO | bytes, **kwargs) -> DocumentExtractionResponse`. Mọi Extractor phải implement.
- **Capability Scoring (Optional):** Phương thức `score_capability(page_type, language, is_complex) -> float` để Dispatcher tự động chọn Extractor tối ưu nhất.
- **Import-on-Demand:** Docling và PaddleOCR là optional dependencies nhóm `[extractors]` trong `pyproject.toml`. Extractor kiểm tra `importlib.util.find_spec()` trước khi import. Nếu thư viện không có → HTTP 501 Not Implemented.
- **Memory Contract:** Mọi Extractor bắt buộc gọi `force_garbage_collection_and_trim()` trong khối `finally` sau khi xong việc.

## 3. Đặc tả Frontend (UI 3 Cột)
- **Upload & Config:** Form tải tệp hỗ trợ định dạng (PDF, PNG, JPG, JPEG). Cho phép thiết lập DPI (72, 150, 300) và ngưỡng Threshold (0.1 - 1.0).
- **Viewport Visualization:** Render PDF trên thẻ Canvas. Gọi API và map Bounding Boxes lên toạ độ hiển thị (Scale chuẩn hoá). Tương tác Hover hai chiều giữa Danh sách kết quả và BBox.
- **Polling Cơ chế:** Poll liên tục `GET /api/v1/health` định kỳ 5s. Nếu models `ready`, đổi badge trạng thái sang "Connected & Ready". Hiển thị thêm RAM usage nếu có.

## 4. Đặc tả Middleware phòng thủ (Upload Guard)
- **Early Backpressure:** Bắt đầu bằng biến đếm toàn cục. Nếu số lượng request đang xử lý $> 10$, trả về HTTP 429 Too Many Requests (kèm header `Retry-After`).
- **Memory-Aware Backpressure:** Ngoài kiểm tra slot, kiểm tra thêm RSS hiện tại. Nếu `current_rss > MEMORY_HARD_LIMIT`, trả về HTTP 503 Service Unavailable kèm `Retry-After: 30` kể cả khi còn slot trống.
- **Disk DoS Guard:** Trích xuất luồng Stream bytes. Nếu Content-Length $> 50MB$ hoặc chunks $\ge 50MB$, đóng kết nối ngay lập tức và trả về HTTP 413 Payload Too Large. Cấm file tạm nằm rác trong thư mục hệ điều hành, cấu hình ép thư mục tmp về `backend/temp/`.
