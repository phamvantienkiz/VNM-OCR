# Report: Review & Chỉnh Sửa Tài Liệu Sản Phẩm — Release 1

> **Ngày:** 30/09/2026  
> **Phiên bản Review:** v1.0  
> **Phạm vi:** Toàn bộ tài liệu trong `docs/implementation/release-1/` và `docs/plan/`  
> **Người thực hiện:** AI Assistant (Antigravity)

---

## 1. Tổng quan & Bối cảnh Review

### 1.1. Mục tiêu Review
Rà soát toàn diện tất cả tài liệu đặc tả sản phẩm (PRD, SRS, TDD, QA Test Cases) và các kế hoạch kỹ thuật (Backend Refactoring Plan, Resource Optimization Plan, UI Redesign Plan) để đảm bảo:

1. **Phù hợp với ràng buộc phần cứng thực tế:** Dự án ưu tiên chạy trên **laptop CPU-only 16GB RAM**, ứng dụng chiếm tối đa **4GB RAM** (tốt nhất 2GB).
2. **Sẵn sàng cho VLM pathway:** Tài liệu phản ánh khả năng tích hợp VLM (Vision Language Model) cho OCR nâng cao trong tương lai, với phân tích khả thi về giới hạn 4GB RAM.
3. **Nguyên tắc an toàn tuyệt đối:** Không bao giờ freeze/treo máy/chiếm 99% RAM.
4. **Nhất quán giữa các tài liệu:** PRD ↔ SRS ↔ TDD ↔ Test Cases phải đồng bộ về con số, khái niệm, và giới hạn.

### 1.2. Tài liệu đã Review

| # | File | Đường dẫn | Vai trò |
|---|------|-----------|---------|
| 1 | PRD | [`prd.md`](file:///E:/MyProject/VNM-OCR/docs/implementation/release-1/prd.md) | Yêu cầu sản phẩm |
| 2 | SRS | [`srs.md`](file:///E:/MyProject/VNM-OCR/docs/implementation/release-1/srs.md) | Đặc tả phần mềm |
| 3 | TDD | [`technical-design.md`](file:///E:/MyProject/VNM-OCR/docs/implementation/release-1/technical-design.md) | Thiết kế kỹ thuật |
| 4 | Test Cases | [`test-cases.md`](file:///E:/MyProject/VNM-OCR/docs/implementation/release-1/qa/test-cases.md) | Kiểm thử |
| 5 | Backend Plan | [`fastapi_backend_refactoring_plan.md`](file:///E:/MyProject/VNM-OCR/docs/plan/fastapi_backend_refactoring_plan.md) | Kế hoạch backend |
| 6 | Resource Plan | [`resource_constrained_ocr_optimization_plan.md`](file:///E:/MyProject/VNM-OCR/docs/plan/resource_constrained_ocr_optimization_plan.md) | Kế hoạch tối ưu tài nguyên |
| 7 | UI Plan | [`ui_3column_redesign_plan.md`](file:///E:/MyProject/VNM-OCR/docs/plan/ui_3column_redesign_plan.md) | Kế hoạch giao diện |
| 8 | Init | [`init.md`](file:///E:/MyProject/VNM-OCR/docs/plan/init.md) | Hub chỉ mục tài liệu |

---

## 2. Tổng hợp các Vấn đề Phát hiện & Chỉnh sửa

### 2.1. PRD (`prd.md`) — 7 vấn đề, đã sửa toàn bộ

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới | Lý do sửa |
|---|--------|--------|-------------|-------------|------------|
| P-01 | **Giới hạn RAM đơn tầng, không phản ánh thực tế VLM** | 🔴 Nghiêm trọng | `≤ 2GB RAM Peak` là giới hạn duy nhất | Phân tầng: **Tier 1 (ONNX): ≤2GB**, **Tier 2 (VLM): ≤4GB** | ONNX-only ~350MB models + inference = 1.2–1.5GB. Nhưng VLM 2B quantized INT4 cần thêm 1.5–2.5GB → Cần 2 tier rõ ràng. Nếu chỉ giới hạn 2GB thì tương lai không thể tích hợp VLM. |
| P-02 | **Thiếu ràng buộc phần cứng mục tiêu** | 🔴 Nghiêm trọng | Không nêu rõ target hardware | Thêm mục: Laptop 16GB RAM, ứng dụng **tối đa 4GB** (tốt nhất ≤2GB), còn ≥12GB cho OS | Đây là yêu cầu cốt lõi từ stakeholder — phải nêu rõ ràng. |
| P-03 | **Thiếu nguyên tắc an toàn tuyệt đối** | 🔴 Nghiêm trọng | Chỉ nói "không crash/OOM" | Thêm mục 5.3: **KHÔNG BAO GIỜ** freeze/hang/chiếm ≥90% RAM. Chấp nhận chậm, chấp nhận HTTP 503, nhưng **KHÔNG chấp nhận treo máy** | User yêu cầu tường minh: cho phép chậm nhưng không được cứng/treo máy. |
| P-04 | **Thiếu VLM pathway** | 🟡 Quan trọng | Không đề cập VLM | Thêm mục 3.3: VLM OCR Pathway (Future Phase 5+) — kiến trúc extensible, graceful degradation | Docs research đã đề cập VLM (PaddleOCR-VL, Qwen). Cần phản ánh trong PRD để kiến trúc chuẩn bị sẵn. |
| P-05 | **Memory Budget Monitor chưa có trong PRD** | 🟡 Quan trọng | Chỉ có GC/malloc_trim | Thêm bullet: Memory Budget Monitor — giám sát RSS, auto throttle khi gần ngưỡng | Resource Plan v4.5.0 đã thiết kế nhưng PRD không phản ánh. |
| P-06 | **Typo "Bô điều phối"** | 🟢 Nhỏ | "Bô điều phối" | "**Bộ** điều phối" | Lỗi chính tả. |
| P-07 | **Out-of-scope thiếu Training** | 🟢 Nhỏ | Chỉ 2 mục | Thêm: "Training / Fine-tuning mô hình (chỉ inference)" | Làm rõ ranh giới scope. |

### 2.2. SRS (`srs.md`) — 6 vấn đề, đã sửa toàn bộ

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới | Lý do sửa |
|---|--------|--------|-------------|-------------|------------|
| S-01 | **Thiếu Memory Budget Monitor spec** | 🔴 Nghiêm trọng | Chỉ có GC sau request | Thêm mục 2.2: Memory Budget Monitor với 3 ngưỡng (Soft 2GB, Hard 3.5GB, Critical 90% total RAM) | Đây là cơ chế then chốt đảm bảo ứng dụng không bao giờ chiếm quá 4GB. Resource Plan v4.5.0 đã thiết kế chi tiết nhưng SRS không phản ánh. |
| S-02 | **Fast Path ghi "PyMuPDF" sai thực tế** | 🔴 Nghiêm trọng | `Fast Path (PyMuPDF trích xuất text trực tiếp)` | `Fast Path (pdfplumber trích xuất text trực tiếp)` | Backend Plan v1.4.0 và Resource Plan v4.5.0 đều dùng `pdfplumber` (MIT License). PyMuPDF có giấy phép AGPL, đã bị loại bỏ. Nhưng SRS cũ vẫn ghi PyMuPDF — mâu thuẫn nghiêm trọng. |
| S-03 | **Thiếu Memory-Aware Backpressure** | 🟡 Quan trọng | Middleware chỉ check slot + file size | Thêm: kiểm tra RSS hiện tại, nếu > HARD_LIMIT → HTTP 503 kể cả khi còn slot | Slot-based backpressure không đủ — nếu request trước dùng nhiều RAM chưa kịp thu hồi, request mới vẫn lọt vào. |
| S-04 | **Thiếu VLM extensible architecture** | 🟡 Quan trọng | Không đề cập | Thêm mục 2.5: BaseRecognizer interface, config-driven selection, VLM Loading Guard | Chuẩn bị kiến trúc cho Phase 5+. |
| S-05 | **Health endpoint không report RAM** | 🟡 Quan trọng | Chỉ report models ready | Thêm: `rss_mb`, `memory_budget_status` trong health response | Cần để frontend hiển thị và để ops monitoring. |
| S-06 | **Thiếu context "chạy trên laptop 16GB"** | 🟢 Nhỏ | Không nêu | Thêm vào phần Giới thiệu | Alignment với PRD mới. |

### 2.3. TDD (`technical-design.md`) — 5 vấn đề, đã sửa toàn bộ

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới | Lý do sửa |
|---|--------|--------|-------------|-------------|------------|
| T-01 | **Queue timeout 10s quá ngắn cho VLM** | 🔴 Nghiêm trọng | `asyncio.timeout(10)` — Queue timeout 10s | `asyncio.timeout(30)` — Queue timeout 30s | VLM inference trên CPU có thể mất 5–30s/trang. Nếu queue timeout chỉ 10s, VLM request sẽ bị reject liên tục. |
| T-02 | **Sequence Diagram thiếu Memory Monitor** | 🟡 Quan trọng | Không có MemoryMonitor participant | Thêm `MemoryMonitor` participant: check RSS trước accept, check RSS sau mỗi page | Phản ánh thiết kế Memory Budget Monitor từ SRS. |
| T-03 | **Thiếu BaseRecognizer interface** | 🟡 Quan trọng | Chỉ có BaseExtractor | Thêm `BaseRecognizer` interface với `recognize()` và `get_memory_requirement()` | Chuẩn bị cho VLM extensibility. |
| T-04 | **Thiếu MemoryBudgetMonitor class** | 🟡 Quan trọng | Không có | Thêm class với `get_rss_mb()`, `check_can_accept_request()`, `check_can_load_model()`, `get_budget_status()` | Concrete class design cho SRS mục 2.2. |
| T-05 | **Thiếu Memory Config section** | 🟡 Quan trọng | Không có | Thêm mục 5: Memory Budget Configuration với soft/hard/critical limits, VLM config | Hoàn thiện thiết kế cấu hình. |

### 2.4. Test Cases (`test-cases.md`) — 6 vấn đề, đã sửa toàn bộ

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới | Lý do sửa |
|---|--------|--------|-------------|-------------|------------|
| Q-01 | **Thiếu test "không treo máy" (No-Freeze Test)** | 🔴 Nghiêm trọng | Chỉ test RAM peak và reclaim | Thêm **TC-09**: Chạy OCR + Chrome + VS Code + Notepad đồng thời, Windows không "Not Responding" | Đây là yêu cầu quan trọng nhất của user: "không được làm cứng, treo máy". |
| Q-02 | **Thiếu test Memory Budget Monitor** | 🔴 Nghiêm trọng | Không có | Thêm **TC-04**: Test graceful degradation khi RAM gần ngưỡng (HTTP 503 + thu hồi) | Đảm bảo Memory Budget Monitor hoạt động đúng. |
| Q-03 | **Thiếu test VLM Tier 2** | 🟡 Quan trọng | Không có | Thêm **TC-03**: Test VLM RAM ≤4GB, chấp nhận chậm, kiểm tra bằng gõ Notepad song song | Chuẩn bị test case cho Phase 5+. |
| Q-04 | **Thiếu test Health endpoint memory** | 🟡 Quan trọng | Không có | Thêm **TC-07**: Verify health response chứa `rss_mb`, `budget_status` | Đảm bảo monitoring hoạt động. |
| Q-05 | **Thiếu Ma trận tài nguyên đa nền tảng** | 🟡 Quan trọng | Chỉ liệt kê 5 môi trường | Thêm bảng chi tiết: RAM cho phép, hành vi khi vượt ngưỡng cho từng nền tảng | Làm rõ expectation khác nhau theo hardware. |
| Q-06 | **TC-02 thiếu kiểm tra tổng RAM 4GB** | 🟢 Nhỏ | Chỉ check process peak ≤2GB | Thêm: "Tổng RAM bị chiếm bởi process KHÔNG BAO GIỜ vượt 4GB" | Alignment với PRD 5.3. |

---

## 3. Phân tích Cross-Reference: Docs Plan vs Docs Implementation

### 3.1. Điểm đồng bộ tốt ✅

| Khía cạnh | Plan | Implementation | Đánh giá |
|-----------|------|----------------|----------|
| ONNX-Only, No PyTorch Production | Backend Plan v1.4.0 ✓ | PRD/SRS ✓ | Nhất quán |
| Lazy Loading 6 models | Resource Plan v4.5.0 ✓ | SRS 2.1 ✓ | Nhất quán |
| Thread Budget (2 threads) | Resource Plan ✓ | TDD ✓ | Nhất quán |
| pdfplumber (MIT, không PyMuPDF) | Resource Plan v4.5.0 ✓ | SRS ✓ (đã sửa) | Nhất quán sau sửa |
| Streaming page generator | Resource Plan ✓ | TDD Sequence ✓ | Nhất quán |
| Cross-platform GC | Resource Plan ✓ | SRS/TDD ✓ | Nhất quán |
| ASGI Middleware tách biệt | Resource Plan v4.5.0 ✓ | SRS 4 ✓ | Nhất quán |

### 3.2. Điểm mâu thuẫn đã phát hiện & giải quyết ⚠️

| # | Mâu thuẫn | Plan nói | Implementation nói (trước sửa) | Giải quyết |
|---|-----------|----------|-------------------------------|------------|
| 1 | **PyMuPDF vs pdfplumber** | Resource Plan: dùng pdfplumber (MIT) | SRS cũ: "PyMuPDF trích xuất" | Sửa SRS → pdfplumber |
| 2 | **RAM Budget 2GB cứng vs linh hoạt** | Resource Plan: "Hard constraint 2GB" | PRD cũ: "≤ 2GB Peak" duy nhất | Sửa PRD → Phân tầng Tier 1/Tier 2 |
| 3 | **Queue timeout** | Resource Plan: timeout 10s queue | TDD cũ: timeout 10s | Sửa TDD → 30s (hỗ trợ VLM tương lai) |
| 4 | **Endpoint path format** | Backend Plan: `/api/v1/ocr`, `/api/v1/document/extract` | PRD: `/api/v1/extract/ocr`, `/api/v1/extract/table` | **Chưa sửa — Cần quyết định:** Backend Plan dùng format `/api/v1/{resource}`, PRD dùng `/api/v1/extract/{type}`. Xem khuyến nghị mục 4.2. |

### 3.3. Điểm Plan có nhưng Implementation thiếu (đã bổ sung) ➕

| # | Nội dung | Plan nguồn | Bổ sung vào |
|---|----------|------------|-------------|
| 1 | Memory Budget Monitor | Resource Plan mục 2 (Hard Constraints) | SRS 2.2, TDD 2.1, Test Cases TC-04 |
| 2 | VLM pathway extensible | Research: smart_pdf_classification | PRD 3.3, SRS 2.5, TDD 2.1 |
| 3 | No-freeze test | User requirement (mới) | Test Cases TC-09 |
| 4 | Health endpoint + RAM | Resource Plan benchmarks | SRS 2.4, Test Cases TC-07 |

---

## 4. Phân tích Khả thi: VLM OCR trong Giới hạn 4GB RAM

### 4.1. Bảng Ước lượng RAM cho các VLM Pathway

| Model | Params | Quantization | Ước lượng RAM (CPU) | + ONNX Baseline (~500MB) | Tổng Peak | Trong ngưỡng 4GB? |
|-------|--------|-------------|---------------------|--------------------------|-----------|-------------------|
| Qwen2-VL-2B | 2B | INT4 (GPTQ/AWQ) | ~1.5GB | 2.0GB | **~2.0GB** | ✅ Thoải mái |
| Florence-2-base | 0.23B | FP16 | ~0.5GB | 1.0GB | **~1.0GB** | ✅ Rất thoải mái |
| PaddleOCR-VL | ~1B | FP32 | ~2.0GB | 2.5GB | **~2.5GB** | ✅ Trong ngưỡng |
| Qwen2-VL-7B | 7B | INT4 | ~4.5GB | 5.0GB | **~5.0GB** | ❌ Vượt ngưỡng |
| Phi-3-Vision | 4.2B | INT4 | ~3.0GB | 3.5GB | **~3.5GB** | ⚠️ Sát ngưỡng |

### 4.2. Kết luận VLM
- **Khả thi trong 4GB:** Các model ≤2B params với quantization INT4 hoàn toàn nằm trong ngưỡng.
- **Không khả thi:** Các model ≥7B params, kể cả quantized, sẽ vượt ngưỡng trên laptop 16GB.
- **Khuyến nghị:** Ưu tiên Florence-2-base (nhẹ nhất) hoặc Qwen2-VL-2B INT4 (cân bằng chất lượng/tài nguyên).
- **Tốc độ:** Trên CPU, VLM 2B sẽ mất 5–30 giây/trang. Chấp nhận được theo yêu cầu "cho phép chậm nhưng không được treo".
- **Cơ chế an toàn bắt buộc:**
  - Kiểm tra `available_ram` trước khi nạp VLM model.
  - Nếu không đủ → auto fallback về ONNX-only.
  - Memory-aware processing: sau mỗi page, check RSS và trigger GC nếu cần.

---

## 5. Khuyến nghị Hành động Tiếp theo

### 5.1. Cần quyết định ngay (Blocking)

| # | Quyết định | Tác động | Đề xuất |
|---|-----------|---------|---------|
| 1 | **Chuẩn hóa Endpoint Path** | Backend Plan dùng `/api/v1/ocr`, PRD dùng `/api/v1/extract/ocr` | **Đề xuất:** Dùng format Backend Plan (`/api/v1/ocr`, `/api/v1/document/extract`) vì đã triển khai trong code và khớp với UI Plan. Cập nhật lại PRD/SRS sau quyết định. |
| 2 | **Thêm `psutil` vào base dependencies** | Cần cho Memory Budget Monitor (cross-platform) | **Đề xuất:** Thêm `psutil>=5.9.0` vào `[project.dependencies]` trong `pyproject.toml` (không chỉ `[dev]`). |

### 5.2. Cần thực hiện sớm (High Priority)

| # | Hành động | File tác động |
|---|----------|---------------|
| 1 | Implement `MemoryBudgetMonitor` class | `backend/app/utils/memory_utils.py` (mở rộng) |
| 2 | Thêm memory config vào `Settings` | `backend/app/core/config.py` |
| 3 | Tích hợp RAM reporting vào `/api/v1/health` | `backend/app/api/v1/endpoints/health.py` |
| 4 | Thêm memory check vào Middleware | `backend/app/middlewares/upload_guard.py` |
| 5 | Viết test `test_resource_budget.py` | `backend/tests/test_resource_budget.py` |

### 5.3. Cần cập nhật thêm (Medium Priority)

| # | Hành động | Chi tiết |
|---|----------|---------|
| 1 | Cập nhật `docs/plan/init.md` | Thêm link đến report này |
| 2 | Đồng bộ endpoint paths | Sau khi quyết định mục 5.1.1 |
| 3 | Cập nhật Resource Plan v4.5.0 | Bổ sung VLM tier vào Hard Constraints table |
| 4 | Cập nhật UI Plan | Hiển thị RAM usage từ health endpoint lên Topbar |

---

## 6. Tóm tắt Thay đổi Định lượng

| Chỉ số | Trước Review | Sau Review |
|--------|-------------|------------|
| Số vấn đề phát hiện | 0 | **24** |
| Mức Nghiêm trọng (🔴) | — | **8** |
| Mức Quan trọng (🟡) | — | **12** |
| Mức Nhỏ (🟢) | — | **4** |
| File đã chỉnh sửa | 0 | **4** (PRD, SRS, TDD, Test Cases) |
| Mâu thuẫn cross-ref | Không rõ | **4** (3 đã sửa, 1 cần quyết định) |
| Test Cases mới | 0 | **+5** (TC-03, TC-04, TC-07, TC-09 + Ma trận) |
| VLM khả thi trong 4GB | Chưa phân tích | **Florence-2, Qwen2-VL-2B INT4: ✅ Khả thi** |
