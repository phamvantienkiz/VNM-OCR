# Product Requirements Document (PRD) - Release 1

## 1. Tóm tắt dự án (Executive Summary)
Mục tiêu của Release 1 là xây dựng và hoàn thiện **VNM-OCR Core**, một hệ thống bóc tách dữ liệu tài liệu (OCR, Bố cục, Bảng biểu) chất lượng cao, tối ưu hóa cho tiếng Việt. Hệ thống được thiết kế đặc biệt như một **vi dịch vụ (microservice)** cực nhẹ để tích hợp vào các hệ thống RAG (Retrieval-Augmented Generation) và AI Agents, **ưu tiên chạy local trên laptop CPU với RAM tiêu chuẩn 16GB**.

## 2. Mục tiêu sản phẩm (Product Goals)
- **Hiệu năng & Tài nguyên (Phân tầng — Tiered Resource Budget):**
  - **Tier 1 — ONNX-Only Pipeline (Release 1 Core):** Hoạt động ổn định với Tối đa 1 Uvicorn Worker, $\le 200\%$ CPU, **$\le 2GB$ RAM Peak** (mục tiêu lý tưởng). Đây là chế độ mặc định.
  - **Tier 2 — VLM-Augmented Pipeline (Future Pathway):** Cho phép tích hợp VLM (Vision Language Model) cho OCR nâng cao, **$\le 4GB$ RAM Peak**. Chấp nhận tốc độ chậm hơn nhưng **tuyệt đối không được đóng băng (freeze), treo máy (hang), hoặc chiếm $\ge 90\%$ tổng RAM hệ thống** khiến người dùng không thể thao tác.
- **Ràng buộc phần cứng mục tiêu (Target Hardware Constraint):**
  - Laptop CPU-only, 16GB RAM: Ứng dụng chỉ được chiếm **tối đa 4GB RAM** (tốt nhất $\le 2GB$), đảm bảo còn $\ge 12GB$ cho hệ điều hành và các ứng dụng khác.
  - Server / GPU: Không giới hạn cứng nhưng vẫn tuân thủ nguyên tắc tiết kiệm tài nguyên.
- **Khả năng tương thích:** Chạy mượt mà trên 5 nền tảng phần cứng chính (Windows CPU, Mac Apple Silicon, Linux CPU, Windows RTX GPU, Linux RTX GPU).
- **Chất lượng bóc tách:** Bảo toàn 100% độ chính xác mô hình FP32 cho tiếng Việt.
- **Phân loại Thông minh:** Áp dụng thuật toán Smart PDF Classification để tự động phân luồng xử lý tài liệu (Digital, Scanned, Complex, Corrupted) nhằm tiết kiệm 80% thời gian với Fast Path.
- **Giao diện Người dùng:** Giao diện 3 cột trực quan (Tải lên, Xem trước, Kết quả Markdown/JSON), báo cáo Health Status theo thời gian thực.

## 3. Phạm vi tính năng (In-Scope Features)

### 3.1. Core OCR & Backend Engine (Phase 1 & 3)
- Hỗ trợ tải trễ (Lazy Loading / On-Demand Instantiation) cho 6 mô hình ONNX Core: `det`, `cnn`, `encoder`, `decoder`, `layout`, `tsr`.
- Giới hạn luồng khắt khe (Thread locking): `OMP_NUM_THREADS=2`, `VECLIB_MAXIMUM_THREADS=1`.
- Quản trị bộ nhớ ép buộc đa nền tảng: `gc.collect()`, `libc.malloc_trim(0)` (Linux), `malloc_zone_pressure_relief` (Mac), `kernel32.HeapCompact` (Windows).
- **Memory Budget Monitor:** Cơ chế giám sát RSS liên tục, tự động throttle (giảm tốc / từ chối request mới) khi RAM tiến gần ngưỡng cứng ($\ge 3.5GB$ trên laptop 16GB).
- Middleware phòng thủ: `StreamingUploadGuardMiddleware` chặn File > 50MB và Early Backpressure (Max 10 active slots).

### 3.2. Smart PDF Classification & Hybrid Extraction (Phase 4)
- **SmartPDFInspector:** Thuật toán duyệt trước tài liệu để tính điểm SCS (Scanned Content Score), từ đó phân loại: Tài liệu sinh số (Digital), Tài liệu Scan (Scanned), Tài liệu Hỏng (Corrupted), Tài liệu Phức tạp (Complex).
- **UniversalDocumentDispatcher:** Bộ điều phối tự động quyết định luồng bóc tách (Fast Path không qua GPU cho Digital, hoặc Deep OCR cho Scanned).
- **Explicit Endpoints:** Cung cấp API chuyên biệt `/api/v1/extract/ocr`, `/api/v1/extract/layout`, `/api/v1/extract/table` cho client.

### 3.3. VLM OCR Pathway (Future — Phase 5+)
> **Ghi chú:** Phần này nằm ngoài Release 1 nhưng kiến trúc phải **sẵn sàng mở rộng** (extensible) để tích hợp VLM mà không cần refactor lại core.
- Tích hợp VLM nhẹ (ví dụ: Qwen2-VL-2B quantized, Florence-2, PaddleOCR-VL) làm bộ recognizer thay thế hoặc bổ sung cho ONNX pipeline.
- **RAM Budget cho VLM:** Model 2B quantized INT4 chiếm khoảng 1.5–2.5GB VRAM/RAM. Kết hợp với ONNX pipeline (~500MB baseline), tổng peak dự kiến $\le 3.5GB$ — nằm trong ngưỡng 4GB cho phép.
- Cơ chế **Graceful Degradation:** Nếu phát hiện RAM không đủ cho VLM, tự động fallback về ONNX-only pipeline và log cảnh báo.

### 3.4. Giao diện UI 3 cột (Phase 2)
- Layout CSS Grid chia 3 phần: Upload/Config, Viewport Canvas (Overlay BBox), Results (Markdown, Items, JSON).
- Smart Health Polling tự động kiểm tra trạng thái khởi tạo ONNX Models.
- Điều khiển hủy Request tự động (AbortController) khi đổi file.
- Giao diện thân thiện WCAG 2.2 AA.

## 4. Ngoài phạm vi (Out-of-Scope)
- Quản lý người dùng, đăng nhập, phân quyền (Authentication / Authorization).
- Lưu trữ cơ sở dữ liệu vĩnh viễn (Chỉ lưu file tạm trong phiên request và dọn dẹp ngay).
- Training / Fine-tuning mô hình (chỉ inference).

## 5. Các chỉ số thành công (Success Metrics - KPIs)

### 5.1. Tier 1 — ONNX-Only (Release 1 Core)
| Chỉ số | Mục tiêu | Ghi chú |
|--------|----------|---------|
| RAM Peak (PDF 30 trang, 150 DPI) | $\le 1.5GB$ | Mục tiêu lý tưởng cho laptop CPU |
| RAM Peak (PDF 50 trang, 150 DPI) | $\le 2.0GB$ | Giới hạn cứng Tier 1 |
| Thu hồi RAM về baseline | $\le 2s$ | Sau khi kết thúc request |
| Fast Path (Digital PDF) | $< 50ms$/trang | Không qua ONNX inference |
| Concurrent requests | 10 requests | Trả HTTP 429/503 đúng chuẩn, không crash/OOM |

### 5.2. Tier 2 — VLM-Augmented (Future, nhưng kiến trúc chuẩn bị từ bây giờ)
| Chỉ số | Mục tiêu | Ghi chú |
|--------|----------|---------|
| RAM Peak (VLM inference) | $\le 4.0GB$ | Trên laptop 16GB, còn $\ge 12GB$ cho OS |
| Tốc độ | Chấp nhận chậm (5–30s/trang) | Không freeze/treo máy |
| Fallback | Tự động về ONNX-only | Khi RAM $\ge 3.5GB$ trước khi nạp VLM |

### 5.3. Nguyên tắc An toàn Tuyệt đối
- **KHÔNG BAO GIỜ** chiếm $\ge 90\%$ tổng RAM hệ thống (trên laptop 16GB = không vượt ~14GB).
- **KHÔNG BAO GIỜ** gây freeze/hang/not responding cho hệ điều hành.
- Chấp nhận chậm, chấp nhận từ chối request (HTTP 503), nhưng **KHÔNG chấp nhận treo máy**.
