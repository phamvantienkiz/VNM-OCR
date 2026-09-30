# Software Requirements Specification (SRS) - Release 1

## 1. Giới thiệu
Tài liệu này đặc tả các yêu cầu phần mềm chi tiết cho VNM-OCR Release 1, tập trung vào kiến trúc phân luồng, kiểm soát tài nguyên phần cứng, và logic bóc tách tài liệu thông minh. Hệ thống được thiết kế ưu tiên chạy trên **laptop CPU-only 16GB RAM** với ngân sách bộ nhớ phân tầng.

## 2. Đặc tả Tính năng Backend & API

### 2.1. Quản lý Vòng đời & Tải trễ (Lazy Loading)
- **Cơ chế nạp Model:** ONNX Sessions không được nạp toàn bộ lúc khởi động (startup). Khởi tạo `EngineManager` dạng Singleton. Các engine (`OcrEngine`, `LayoutEngine`, `TableEngine`) chỉ nạp trọng số tương ứng khi có request API đầu tiên chạm vào endpoint cần dùng nó.
- **Hardware Matrix Detection:** Khởi chạy `get_available_providers()`. Tự động ưu tiên: `CUDAExecutionProvider` $\rightarrow$ `CoreMLExecutionProvider` $\rightarrow$ `CPUExecutionProvider`.
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

### 2.3. Smart PDF Inspector & Hybrid Dispatcher
- **Mô tả:** Mô-đun phân tích cú pháp PDF nội tại.
- **Quy trình hoạt động:**
  1. Trích xuất ngẫu nhiên max 3 trang từ tài liệu tải lên.
  2. Phân tích Tỷ lệ Văn bản số (Text Fraction) / Raster Image Fraction.
  3. Tính điểm SCS (Scanned Content Score).
  4. Nếu $SCS \ge 0.7$: Gán loại `SCANNED_DOCUMENT`.
  5. Nếu $SCS \le 0.1$: Gán loại `DIGITAL_DOCUMENT`.
  6. Nếu phát hiện font dị hình, vector mã hóa sai: Gán `CORRUPTED_VECTOR`.
- **UniversalDispatcher Routing:**
  - `DIGITAL_DOCUMENT`: Điều hướng sang Fast Path (PyMuPDF / pdfplumber trích xuất text trực tiếp), bỏ qua ONNX.
  - `SCANNED_DOCUMENT`: Điều hướng sang Heavy Pipeline (Render ra ảnh $\rightarrow$ Layout Detection $\rightarrow$ OCR $\rightarrow$ Markdown).

### 2.4. Endpoints Chuyên biệt (Explicit Endpoints)
Hệ thống cung cấp danh sách Endpoints độc lập theo chuẩn thiết kế API:
- `POST /api/v1/extract/ocr`: Nhận diện text từ ảnh.
- `POST /api/v1/extract/layout`: Trả về Bounding Box cấu trúc.
- `POST /api/v1/extract/table`: Trích xuất HTML/Markdown bảng biểu.
- `POST /api/v1/extract/smart-document`: Tự động kích hoạt luồng Hybrid Inspector.
- `GET /api/v1/health`: Health check kèm thông tin RAM usage (`rss_mb`, `memory_budget_status`).

### 2.5. Kiến trúc Extensible cho VLM (Future-Ready)
- **Interface `BaseRecognizer`:** Định nghĩa contract chung cho cả ONNX Recognizer và VLM Recognizer, cho phép swap runtime.
- **Config-driven Selection:** Chọn recognizer backend qua biến môi trường `OCR_RECOGNIZER_BACKEND=onnx|vlm` (mặc định `onnx`).
- **VLM Loading Guard:** Trước khi nạp VLM model, kiểm tra `available_ram = total_ram - current_rss`. Nếu `available_ram < VLM_MIN_RAM_REQUIRED` (mặc định 3GB), từ chối nạp và fallback về ONNX.

## 3. Đặc tả Frontend (UI 3 Cột)
- **Upload & Config:** Form tải tệp hỗ trợ định dạng (PDF, PNG, JPG, JPEG). Cho phép thiết lập DPI (72, 150, 300) và ngưỡng Threshold (0.1 - 1.0).
- **Viewport Visualization:** Render PDF trên thẻ Canvas. Gọi API và map Bounding Boxes lên toạ độ hiển thị (Scale chuẩn hoá). Tương tác Hover hai chiều giữa Danh sách kết quả và BBox.
- **Polling Cơ chế:** Poll liên tục `GET /api/v1/health` định kỳ 5s. Nếu models `ready`, đổi badge trạng thái sang "Connected & Ready". Hiển thị thêm RAM usage nếu có.

## 4. Đặc tả Middleware phòng thủ (Upload Guard)
- **Early Backpressure:** Bắt đầu bằng biến đếm toàn cục. Nếu số lượng request đang xử lý $> 10$, trả về HTTP 429 Too Many Requests (kèm header `Retry-After`).
- **Memory-Aware Backpressure:** Ngoài kiểm tra slot, kiểm tra thêm RSS hiện tại. Nếu `current_rss > MEMORY_HARD_LIMIT`, trả về HTTP 503 Service Unavailable kèm `Retry-After: 30` kể cả khi còn slot trống.
- **Disk DoS Guard:** Trích xuất luồng Stream bytes. Nếu Content-Length $> 50MB$ hoặc chunks $\ge 50MB$, đóng kết nối ngay lập tức và trả về HTTP 413 Payload Too Large. Cấm file tạm nằm rác trong thư mục hệ điều hành, cấu hình ép thư mục tmp về `backend/temp/`.
