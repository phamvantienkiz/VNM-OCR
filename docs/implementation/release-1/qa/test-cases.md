# QA & Test Cases - Release 1

## 1. Yêu cầu Môi trường Kiểm thử
- Thực thi trên 5 môi trường: Windows CPU (16GB), MacOS Apple Silicon, Ubuntu CPU, Windows RTX (6GB VRAM), Linux Server RTX (8GB VRAM).
- **Môi trường ưu tiên (Primary Target):** Windows CPU 16GB RAM — đại diện cho laptop tiêu chuẩn của người dùng cuối.
- Công cụ: `pytest`, `psutil`, `locust` (để test tải).

## 2. Danh sách Test Cases cốt lõi (Core Test Cases)

### TC-01: Smart PDF Classification Accuracy
- **Mô tả:** Đưa 3 loại tài liệu PDF vào `/api/v1/extract/smart-document`:
  - 1 file báo cáo kinh tế sinh số 100% (Digital).
  - 1 file hoá đơn đỏ chụp từ điện thoại (Scanned).
  - 1 file luận văn có công thức toán học dị hình (Corrupted).
- **Kỳ vọng:** `SmartPDFInspector` trả về đúng nhãn cho từng file với tốc độ duyệt $< 0.5s$. Luồng Fast Path được kích hoạt tự động cho file Digital.

### TC-02: Peak RAM Limit — Tier 1 ONNX (Windows CPU 16GB)
- **Mô tả:** Chạy OCR luồng Heavy Path cho file PDF 50 trang trên laptop Windows CPU 16GB RAM. Ghi log Memory Usage (RSS) mỗi 0.5s bằng `psutil`.
- **Kỳ vọng:**
  - RAM Peak không bao giờ vượt ngưỡng $2GB$ (kỳ vọng khoảng 1.2GB - 1.5GB).
  - Sau khi có Response (HTTP 200), RAM trả về baseline ($\le 600MB$) trong vòng $2s$.
  - **Tổng RAM hệ thống bị chiếm bởi process KHÔNG BAO GIỜ vượt $4GB$.**
  - Hệ điều hành vẫn responsive (mở Task Manager, chuyển tab Chrome bình thường).

### TC-03: Peak RAM Limit — Tier 2 VLM Budget (Future Test)
- **Mô tả:** Khi VLM pathway được tích hợp, chạy OCR với VLM recognizer trên laptop Windows CPU 16GB RAM.
- **Kỳ vọng:**
  - RAM Peak $\le 4GB$ (tối đa tuyệt đối cho laptop 16GB).
  - Chấp nhận tốc độ chậm (5–30s/trang).
  - **KHÔNG freeze/hang hệ điều hành.** Kiểm tra bằng cách: trong lúc OCR đang chạy, mở Notepad và gõ chữ — phải mượt mà.
  - Nếu RAM gần đạt ngưỡng, hệ thống tự động throttle hoặc fallback về ONNX-only.

### TC-04: Memory Budget Monitor & Graceful Degradation
- **Mô tả:**
  1. Thiết lập `MEMORY_HARD_LIMIT_MB=2048` (giảm xuống 2GB để dễ test).
  2. Gửi request PDF lớn (30 trang scan) để đẩy RAM lên gần ngưỡng.
  3. Trong khi request 1 đang chạy, gửi request 2.
- **Kỳ vọng:**
  1. Request 1 hoàn thành bình thường (có thể chậm do GC chủ động).
  2. Request 2 nhận HTTP 503 với `Retry-After: 30` nếu RAM vượt ngưỡng.
  3. Sau khi request 1 hoàn thành, RAM thu hồi và request mới được chấp nhận.

### TC-05: Early Backpressure & Disk Exhaustion Guard
- **Mô tả:** 
  1. Bắn 15 requests đồng thời bằng Locust. 
  2. Gửi một file giả lập Chunked kích thước 1GB.
- **Kỳ vọng:** 
  1. Request thứ 11 trở đi nhận mã `HTTP 429 Too Many Requests` hoặc `HTTP 503 Server Overloaded`.
  2. Request file 1GB bị ngắt ngay lập tức với mã `HTTP 413 Payload Too Large`.

### TC-06: Lazy Loading Validation
- **Mô tả:** Khởi động Backend. Gọi API `/api/v1/health`. Kiểm tra VRAM/RAM. Sau đó gọi `/api/v1/extract/layout`. Kiểm tra lại VRAM/RAM.
- **Kỳ vọng:** Ở API health, không có trọng số nào được nạp vào RAM. Khi gọi layout, chỉ duy nhất model `layout.onnx` được nạp vào VRAM, không nạp OCR models.

### TC-07: Health Endpoint Memory Reporting
- **Mô tả:** Gọi `GET /api/v1/health` sau khi xử lý xong một request OCR.
- **Kỳ vọng:** Response chứa thông tin RAM:
  ```json
  {
    "status": "ok",
    "models_ready": true,
    "memory": {
      "rss_mb": 520.3,
      "soft_limit_mb": 2048.0,
      "hard_limit_mb": 3584.0,
      "budget_status": "healthy"
    }
  }
  ```

### TC-08: Frontend UI Responsiveness
- **Mô tả:** Mở trình duyệt ở các kích thước Desktop ($1920x1080$), Laptop ($1366x768$), Mobile ($375x667$).
- **Kỳ vọng:** 
  - Tại Desktop, giao diện 3 cột giữ tỉ lệ $25\% / 45\% / 30\%$.
  - Tại Mobile, cột Upload tự động ẩn vào Offcanvas Sidebar (Hamburger menu).

### TC-09: No System Freeze Under Maximum Load
- **Mô tả:** Trên laptop Windows CPU 16GB RAM, đồng thời:
  - Chạy OCR trên PDF 50 trang (150 DPI).
  - Mở Chrome 5 tab, VS Code, và Notepad.
- **Kỳ vọng:**
  - OCR hoàn thành (có thể chậm, chấp nhận 3–5 phút).
  - **Windows KHÔNG hiện "Not Responding"** trên bất kỳ cửa sổ nào.
  - Task Manager báo VNM-OCR process chiếm $< 4GB$ RAM.
  - Người dùng vẫn gõ được chữ trong Notepad mượt mà.

## 3. Khả năng bảo toàn độ chính xác Tiếng Việt
- **TC-10:** Test tập 100 ảnh mẫu (Invoice, CMND, Biên bản) so sánh với output của PaddleOCR gốc (trọng số FP32).
- **Kỳ vọng:** Chuỗi văn bản trả về khớp (Match rate) $100\%$, sai số confidence $\le 0.001$.

## 4. Ma trận Kiểm thử Tài nguyên Đa nền tảng

| Nền tảng | RAM Hệ thống | RAM Peak Cho phép (Ứng dụng) | Hành vi khi vượt ngưỡng |
|----------|-------------|------------------------------|-------------------------|
| Windows CPU Laptop | 16GB | $\le 4GB$ (tốt nhất $\le 2GB$) | HTTP 503 + Retry-After |
| macOS Apple Silicon | 16GB | $\le 4GB$ | GC + malloc_zone_pressure_relief |
| Ubuntu CPU Server | 32GB | $\le 4GB$ (conservative) | HTTP 503 + malloc_trim |
| Windows RTX GPU | 16GB + 6GB VRAM | $\le 2GB$ RAM + GPU offload | CUDA provider tự quản lý VRAM |
| Linux RTX Server | 64GB + 8GB VRAM | $\le 4GB$ RAM | Thoải mái hơn, vẫn giữ kỷ luật |
