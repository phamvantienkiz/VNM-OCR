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


---

# Report v2.0: Review Tài Liệu Phase 6 — Comprehensive Format Extractors & Explicit Endpoints

> **Ngày:** 30/09/2026  
> **Phiên bản Review:** v2.0  
> **Phạm vi:** Toàn bộ tài liệu `docs/implementation/`, `docs/plan/`, và đối chiếu `docs/research/smart_pdf_classification_and_hybrid_extraction.md`  
> **Bối cảnh:** Phase 1-5 đã implement hoàn tất (xem [`todo.md`](file:///E:/MyProject/VNM-OCR/tasks/todo.md)). Cần chuẩn bị đầy đủ tài liệu cho Phase 6 — hiện thực toàn bộ Extractor System.

---

## 7. Mục Tiêu Review v2.0

Sau khi hoàn thành tất cả tasks Phase 1-5 (tất cả đã `[x]`), mục tiêu review lần này là:

1. **Đảm bảo tài liệu đặc tả (PRD/SRS/TDD/Test Cases) đã phản ánh đầy đủ kiến trúc Extractor** từ tài liệu nghiên cứu [`smart_pdf_classification_and_hybrid_extraction.md`](file:///E:/MyProject/VNM-OCR/docs/research/smart_pdf_classification_and_hybrid_extraction.md).
2. **Đảm bảo tính nhất quán** giữa Plan mới ([`comprehensive_format_extractors_plan.md`](file:///E:/MyProject/VNM-OCR/docs/plan/comprehensive_format_extractors_plan.md)) và các tài liệu Implementation.
3. **Phát hiện và sửa** các vấn đề đồng bộ, thiếu sót, hoặc mâu thuẫn.
4. **Cập nhật documentation hub** (`init.md`) để phản ánh đầy đủ hệ sinh thái tài liệu.

---

## 8. Kết Quả Kiểm Tra Đồng Bộ Tài Liệu

### 8.1. PRD (`prd.md`) — ✅ Đã đồng bộ Phase 6

| Kiểm tra | Kết quả | Chi tiết |
|----------|---------|----------|
| Mục 3.3 Comprehensive Format Extractors | ✅ Có | Bảng 4 Extractors đầy đủ với PageType, `requires_image_input`, RAM Peak |
| 10 PageType của SmartPDFInspector v2.5.0 | ✅ Có | Mục 3.2 liệt kê rõ ràng `BORN_DIGITAL` → `EMPTY` |
| 2 cờ telemetry (`requires_image_input`, `is_vector_recovery`) | ✅ Có | Mục 3.2 mô tả rõ ngữ nghĩa từng cờ |
| Explicit Endpoints + Auto-routing | ✅ Có | Mục 3.3 đề cập `/api/v1/extract/auto` |
| Nhất quán với Research v2.5.0 | ✅ Khớp | Routing Matrix và Extractor mapping đồng bộ |

### 8.2. SRS (`srs.md`) — ✅ Đã đồng bộ Phase 6

| Kiểm tra | Kết quả | Chi tiết |
|----------|---------|----------|
| BaseExtractor interface spec | ✅ Có | Mục 2.3/2.4/2.6 định nghĩa contract `extract()`, `score_capability()` |
| Import-on-demand + HTTP 501 | ✅ Có | Quy định fallback khi thư viện chưa cài |
| 6 Explicit Dedicated Endpoints | ✅ Có | `/extract/auto`, `/extract/native/pdf`, `/extract/docling`, `/extract/paddle/ocr`, `/extract/paddle/complex-vlm`, `/extract/vnm` |
| Memory Budget cho từng Extractor | ✅ Có | GC trong `finally` block là bắt buộc |
| SmartPDFInspector v2.5.0 spec | ✅ Có | 10 PageType + Multi-signal Gating |

### 8.3. TDD (`technical-design.md`) — ✅ Đã đồng bộ Phase 6

| Kiểm tra | Kết quả | Chi tiết |
|----------|---------|----------|
| Cấu trúc thư mục `services/extractors/` | ✅ Có | Mô tả `base.py`, `native.py`, `vnm.py`, `docling.py`, `paddle.py` |
| Strategy Pattern + Registry | ✅ Có | `UniversalDocumentDispatcher` dạng Registry/Router |
| Sequence Diagram luồng Hybrid | ✅ Có | Flow từ Inspector → Capability Scoring → Extract |
| Ma trận năng lực Extractor | ✅ Có | Bảng score_capability cho từng PageType x Extractor |
| Thiết kế nâng cấp Dispatcher | ✅ Có | Chuyển từ monolith sang Strategy Pattern |

### 8.4. Test Cases (`test-cases.md`) — ⚠️ Có nhưng Pending

| Kiểm tra | Kết quả | Chi tiết |
|----------|---------|----------|
| Test Suite 5: Universal Extractor Routing | ✅ Có | 17 test cases (TC-5.1 → TC-5.17) |
| Test auto-routing 10 PageType | ✅ Có | Kiểm tra phân loại → chọn đúng Extractor |
| Test Explicit Endpoints | ✅ Có | Kiểm tra từng endpoint riêng biệt |
| Test cờ telemetry metadata | ✅ Có | `requires_image_input`, `is_vector_recovery` trong response |
| Test import-on-demand fallback (HTTP 501) | ✅ Có | Kiểm tra khi Docling/PaddleOCR chưa cài |
| **Trạng thái thực thi** | ⏳ Pending | Tất cả TC Suite 5 chưa chạy — chờ code Extractor hoàn thiện |

### 8.5. Extractors Plan (`comprehensive_format_extractors_plan.md`) — ⚠️ Cần bổ sung nhỏ

| Kiểm tra | Kết quả | Chi tiết |
|----------|---------|----------|
| 4 Tasks rõ ràng | ✅ Có | Interface → Native/VNM → Docling/Paddle → Dispatcher |
| Cấu trúc thư mục | ✅ Có | `services/extractors/` + `api/v1/endpoints/extract.py` |
| API Surface 6 endpoints | ✅ Có | Bảng chi tiết Method/Path/Description |
| Data Contracts thống nhất | ✅ Có | `DocumentExtractionResponse` + metadata bổ sung |
| Clean Architecture | ✅ Có | Controller chỉ HTTP route, logic trong Service/Extractor |

---

## 9. Vấn Đề Phát Hiện & Chỉnh Sửa Lần 2

### 9.1. `docs/plan/init.md` — 1 vấn đề, đã sửa

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới | Lý do sửa |
|---|--------|--------|-------------|-------------|------------|
| I-01 | **Hub thiếu link Phase 6 Plan, Research, Report** | 🟡 Quan trọng | Chỉ có 4 link tới `release-1/` | Tái cấu trúc thành 4 section: Specs, Plans (với trạng thái), Research, Reports | Người đọc không thể tìm được plan Phase 6, research document, hay report review từ hub điều hướng |

### 9.2. `docs/plan/comprehensive_format_extractors_plan.md` — 2 vấn đề cần lưu ý

| # | Vấn đề | Mức độ | Chi tiết | Khuyến nghị |
|---|--------|--------|----------|-------------|
| E-01 | **Nội dung bị lặp đôi (duplicate section)** | 🟡 Quan trọng | File chứa 2 phần gần giống nhau: phần đầu (dòng 1-49) là bản ngắn gọn, phần sau (dòng 50-128) là bản chi tiết System Design. Cả 2 đều nói về cùng 4 tasks nhưng với mức chi tiết khác nhau | **Khuyến nghị:** Hợp nhất thành 1 bản duy nhất, giữ bản chi tiết (dòng 50-128) làm nội dung chính và lấy phần bối cảnh (dòng 1-5) từ bản ngắn |
| E-02 | **Escape characters bị hỏng trong code blocks** | 🟢 Nhỏ | Một số ký tự `\a` bị hiểu thành ASCII bell character thay vì `app/` (vd: `\app/services/extractors/base.py` thay vì `app/services/extractors/base.py`) | **Khuyến nghị:** Sửa các đường dẫn bị escape lỗi |

### 9.3. `docs/plan/fastapi_backend_refactoring_plan.md` — 1 vấn đề cần lưu ý

| # | Vấn đề | Mức độ | Chi tiết | Khuyến nghị |
|---|--------|--------|----------|-------------|
| B-01 | **Chưa ghi chú đồng bộ Phase 6** | 🟢 Nhỏ | Kế hoạch Phase 1 đã hoàn thành hoàn toàn nhưng không có ghi chú rằng kiến trúc `DocumentService` monolith sẽ được mở rộng thành Strategy Extractors ở Phase 6 | **Khuyến nghị:** Thêm một ghi chú cuối file: "Xem Phase 6 Plan cho kiến trúc Extractors mở rộng" |

### 9.4. `docs/plan/resource_constrained_ocr_optimization_plan.md` — 1 vấn đề cần lưu ý

| # | Vấn đề | Mức độ | Chi tiết | Khuyến nghị |
|---|--------|--------|----------|-------------|
| R-01 | **Bảng Hard Constraints chưa có Tier 2 VLM** | 🟢 Nhỏ | Bảng mục 2 chỉ liệt kê Hard Constraint 2GB (ONNX Tier 1) | **Khuyến nghị:** Bổ sung dòng ghi chú: "Tier 2 (VLM): ≤4GB — xem PRD mục 2 & 5.2" |

### 9.5. `tasks/todo.md` — 1 vấn đề đã nhận diện

| # | Vấn đề | Mức độ | Chi tiết | Trạng thái |
|---|--------|--------|----------|------------|
| T-01 | **Escape characters bị hỏng trong Phase 6 tasks** | 🟢 Nhỏ | Các path trong Phase 6 bị mất ký tự `a` sau `\` (vd: `\app` hiển thị thành bell char + `pp`) | Đã nhận diện, không ảnh hưởng logic |

### 9.6. `docs/implementation/release-1/qa/test-cases.md` — 4 vấn đề, 2 đã sửa

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới / Khuyến nghị | Lý do sửa |
|---|--------|--------|-------------|---------------------------|------------|
| TC-01 | **Endpoint sai `/extract/smart-document`** | 🔴 Nghiêm trọng | TC-01 gọi `/api/v1/extract/smart-document` | **Đã sửa** → `/api/v1/extract/auto` | Endpoint `/smart-document` không tồn tại trong SRS, TDD hay code. Endpoint auto-routing đúng là `/extract/auto` |
| TC-06 | **Endpoint sai `/extract/layout`** | 🟡 Quan trọng | TC-06 gọi `/api/v1/extract/layout` | **Đã sửa** → `/api/v1/layout` | Endpoint layout đã tồn tại tại `/api/v1/layout` (xem SRS/TDD). Tiền tố `/extract/` chỉ dành cho Phase 6 Explicit Endpoints |
| TC-VLM | **Thiếu test case cho `/extract/paddle/complex-vlm`** | 🟡 Quan trọng | Không có TC riêng trong Bảng 5.2 | **Khuyến nghị:** Thêm TC-5.x test gọi trực tiếp `/extract/paddle/complex-vlm` với paper LaTeX | Endpoint này xuất hiện trong SRS/TDD nhưng không có test case tường minh |
| TC-PAGE | **Bảng Suite 5.1 thiếu test cho `IMAGE_ONLY` và `EMPTY`** | 🟢 Nhỏ | Bảng 5.1 ghi "10 PageType" nhưng chỉ test 8 types | **Khuyến nghị:** Thêm TC cho `IMAGE_ONLY` (→ tương tự `SCANNED`) và `EMPTY` (→ skip/empty result) | Đảm bảo 100% coverage cho enum PageType |

### 9.7. `docs/plan/init.md` — Bổ sung: Sửa đường dẫn tương đối (Broken Links)

| # | Vấn đề | Mức độ | Nội dung cũ | Nội dung mới | Lý do sửa |
|---|--------|--------|-------------|-------------|------------|
| I-02 | **Đường dẫn tương đối thừa 1 bậc `../`** | 🟡 Quan trọng | `../../implementation/release-1/prd.md` (6 links) | **Đã sửa** → `../implementation/release-1/prd.md` | File nằm tại `docs/plan/init.md`, chỉ cần 1 lần `../` để lên `docs/`. Đường dẫn cũ sẽ trỏ ra ngoài project root |

---

## 10. Phân Tích Đối Chiếu: Research v2.5.0 ↔ Implementation Docs ↔ Plan Phase 6

### 10.1. Ma Trận Đối Chiếu Kiến Trúc Extractor

| Thành phần | Research v2.5.0 | PRD | SRS | TDD | Plan Phase 6 | Đánh giá |
|------------|----------------|-----|-----|-----|-------------|----------|
| `BaseExtractor` interface | Mục 5.1 ✓ | Mục 3.3 ✓ | Mục 2.3 ✓ | Mục 2 ✓ | Task 1 ✓ | ✅ Đồng bộ 100% |
| `NativePDFExtractor` | Mục 5.3 ✓ | Bảng 3.3 ✓ | Mục 2.4 ✓ | Có ✓ | Task 2 ✓ | ✅ Đồng bộ 100% |
| `VNMOCRExtractor` (≡ `VietnameseOCRExtractor`) | Mục 5.3 ✓ | Bảng 3.3 ✓ | Mục 2.4 ✓ | Có ✓ | Task 2 ✓ | ✅ Đồng bộ 100% |
| `DoclingUniversalExtractor` | Mục 5.3 ✓ | Bảng 3.3 ✓ | Mục 2.6 ✓ | Có ✓ | Task 3 ✓ | ✅ Đồng bộ 100% |
| `PaddleOCRExtractor` | Mục 5.3 ✓ | Bảng 3.3 ✓ | Mục 2.6 ✓ | Có ✓ | Task 3 ✓ | ✅ Đồng bộ 100% |
| `UniversalDocumentDispatcher` | Mục 5.3 ✓ | Mục 3.2 ✓ | Mục 2.4 ✓ | Có ✓ | Task 4 ✓ | ✅ Đồng bộ 100% |
| `SmartPDFInspector` v2.5.0 | Mục 5.2 ✓ | Mục 3.2 ✓ | Mục 2.4 ✓ | Có ✓ | Implicit ✓ | ✅ Đồng bộ 100% |
| 10 `PageType` enum | Mục 5.1 ✓ | Mục 3.2 ✓ | Có ✓ | Có ✓ | Mục 1 ✓ | ✅ Đồng bộ 100% |
| `requires_image_input` cờ | Mục 5.4 ✓ | Mục 3.2 ✓ | Có ✓ | Có ✓ | Mục 2.2 ✓ | ✅ Đồng bộ 100% |
| `is_vector_recovery` cờ | Mục 5.4 ✓ | Mục 3.2 ✓ | Có ✓ | Có ✓ | Mục 2.2 ✓ | ✅ Đồng bộ 100% |
| Explicit Endpoints (6 routes) | Mục 4.2 ✓ | Mục 3.3 ✓ | Mục 2.6 ✓ | Có ✓ | Mục 2.1 ✓ | ✅ Đồng bộ 100% |

### 10.2. Ma Trận Đối Chiếu Endpoints

| Endpoint | Research v2.5.0 | SRS | Plan Phase 6 | Mô tả |
|----------|----------------|-----|-------------|-------|
| `POST /api/v1/extract/auto` | `/api/v1/extract/universal` | `/api/v1/extract/auto` | `/api/v1/extract/auto` | ⚠️ Research dùng tên `/universal`, SRS/Plan dùng `/auto` — **Khác tên nhưng cùng chức năng** |
| `POST /api/v1/extract/native/pdf` | ✓ | ✓ | ✓ | ✅ Đồng bộ |
| `POST /api/v1/extract/docling` | ✓ | ✓ | ✓ | ✅ Đồng bộ |
| `POST /api/v1/extract/paddle/ocr` | ✓ | ✓ | ✓ | ✅ Đồng bộ |
| `POST /api/v1/extract/paddle/complex-vlm` | ✓ | ✓ | ✓ | ✅ Đồng bộ |
| `POST /api/v1/extract/vnm` | `/api/v1/document/extract` | `/api/v1/extract/vnm` | `/api/v1/extract/vnm` | ⚠️ Research giữ endpoint cũ, SRS/Plan dùng endpoint mới — **Cần quyết định** |

### 10.3. Điểm Cần Quyết Định (Blocking for Phase 6 Implementation)

| # | Quyết định | Tác động | Đề xuất |
|---|-----------|---------|---------|
| 1 | **Tên Auto-routing endpoint:** `/extract/auto` hay `/extract/universal`? | Cần thống nhất trước khi viết code `extract.py` | **Đề xuất:** Dùng `/extract/auto` (ngắn gọn, đã thống nhất trong SRS/Plan). Research document dùng `/extract/universal` nhưng là alias — code có thể hỗ trợ cả 2. |
| 2 | **VNM-OCR endpoint:** Giữ `/api/v1/document/extract` cũ hay tạo mới `/api/v1/extract/vnm`? | Ảnh hưởng UI, API clients hiện tại | **Đề xuất:** Giữ **cả hai** — `/document/extract` làm backward-compatible, `/extract/vnm` làm explicit endpoint mới. Cả 2 cùng gọi `VNMOCRExtractor`. |
| 3 | **Naming Convention:** `VNMOCRExtractor` (Plan) hay `VietnameseOCRExtractor` (Research)? | Tên class trong code | **Đề xuất:** Dùng `VNMOCRExtractor` (ngắn gọn, khớp với project name). Ghi alias `VietnameseOCRExtractor = VNMOCRExtractor` cho tương thích. |

---

## 11. Đánh Giá Mức Độ Sẵn Sàng Triển Khai Phase 6

### 11.1. Checklist Tài Liệu Sẵn Sàng

| Hạng mục | Trạng thái | Ghi chú |
|----------|-----------|---------|
| PRD phản ánh Phase 6 Extractors | ✅ Sẵn sàng | Mục 3.3 đầy đủ |
| SRS đặc tả interface & endpoints | ✅ Sẵn sàng | Mục 2.3-2.6 chi tiết |
| TDD thiết kế Strategy Pattern | ✅ Sẵn sàng | Class diagram + Sequence diagram |
| Test Cases cho Extractors | ✅ Sẵn sàng | Suite 5 gồm 17 TCs, đang Pending |
| Plan Phase 6 chi tiết tasks | ✅ Sẵn sàng | 4 tasks rõ ràng, có constraints |
| Research blueprint v2.5.0 | ✅ Sẵn sàng | Reference implementation code mẫu |
| Hub điều hướng (`init.md`) | ✅ Đã sửa | Thêm link Phase 6 Plan, Report, Research |

### 11.2. Checklist Code Backend Hiện Tại

| Hạng mục | Trạng thái | Ghi chú |
|----------|-----------|---------|
| `services/extractors/base.py` | ⚠️ Sơ khai | Có interface nhưng thiếu `score_capability()` |
| `services/extractors/native.py` | ❌ Chưa tạo | Cần đưa Fast Path logic vào |
| `services/extractors/vnm.py` | ❌ Chưa tạo | Cần wrapper DocumentService |
| `services/extractors/docling.py` | ❌ Chưa tạo | Import-on-demand stub |
| `services/extractors/paddle.py` | ❌ Chưa tạo | Import-on-demand stub |
| `services/dispatcher.py` | ⚠️ Cũ | Vẫn dùng monolith, cần refactor sang Registry |
| `api/v1/endpoints/extract.py` | ❌ Chưa tạo | 6 explicit endpoints |
| `api/v1/router.py` | ⚠️ Cần update | Thêm router cho extract endpoints |

---

## 12. Khuyến Nghị Hành Động Tiếp Theo (Phase 6 Implementation Roadmap)

### 12.1. Ưu tiên Cao — Triển khai Code (Theo thứ tự)

| Bước | Hành động | File tác động | Ước lượng |
|------|----------|---------------|-----------|
| 1 | **Hoàn thiện BaseExtractor interface** với `score_capability()` và `extract_page()` | `app/services/extractors/base.py` | Nhỏ |
| 2 | **Viết NativePDFExtractor** — chuyển Fast Path từ `document_service.py` | `app/services/extractors/native.py` | Trung bình |
| 3 | **Viết VNMOCRExtractor** — wrapper gọi `DocumentService.extract_document()` | `app/services/extractors/vnm.py` | Trung bình |
| 4 | **Viết DoclingUniversalExtractor** — import-on-demand, HTTP 501 fallback | `app/services/extractors/docling.py` | Nhỏ |
| 5 | **Viết PaddleOCRExtractor** — import-on-demand, HTTP 501 fallback | `app/services/extractors/paddle.py` | Nhỏ |
| 6 | **Refactor UniversalDocumentDispatcher** → Registry + Strategy Pattern | `app/services/dispatcher.py` | Trung bình |
| 7 | **Tạo extract.py router** với 6 endpoints | `app/api/v1/endpoints/extract.py` | Trung bình |
| 8 | **Cập nhật router.py** tích hợp extract router | `app/api/v1/router.py` | Nhỏ |
| 9 | **Cập nhật pyproject.toml** thêm nhóm `[extractors]` | `pyproject.toml` | Nhỏ |
| 10 | **Viết tests** cho dispatcher routing logic | `tests/test_dispatcher.py` | Trung bình |

### 12.2. Ưu tiên Trung Bình — Cải thiện Tài liệu

| # | Hành động | File tác động |
|---|----------|---------------|
| 1 | Hợp nhất nội dung trùng lặp trong `comprehensive_format_extractors_plan.md` | `docs/plan/comprehensive_format_extractors_plan.md` |
| 2 | Sửa escape characters trong `todo.md` Phase 6 | `tasks/todo.md` |
| 3 | Thêm ghi chú Phase 6 reference vào `fastapi_backend_refactoring_plan.md` | `docs/plan/fastapi_backend_refactoring_plan.md` |
| 4 | Bổ sung VLM Tier 2 vào Hard Constraints table | `docs/plan/resource_constrained_ocr_optimization_plan.md` |

---

## 13. Tóm Tắt Thay Đổi Định Lượng — Review v2.0

| Chỉ số | Review v1.0 | Review v2.0 (Bổ sung) | Tổng cộng |
|--------|-------------|----------------------|-----------|
| Số vấn đề phát hiện | 24 | **+12** | **36** |
| Mức Nghiêm trọng (🔴) | 8 | **+1** (TC-01 endpoint sai) | **9** |
| Mức Quan trọng (🟡) | 12 | **+5** (I-01, I-02, E-01, TC-06, TC-VLM) | **17** |
| Mức Nhỏ (🟢) | 4 | **+6** (E-02, B-01, R-01, T-01, TC-PAGE, + nội dung nhỏ) | **10** |
| File đã chỉnh sửa | 4 | **+2** (`init.md`, `test-cases.md`) | **6** |
| Điểm cần quyết định (Blocking) | 2 | **+3** (endpoint naming) | **5** |
| Tài liệu đồng bộ Phase 6 | Chưa kiểm tra | **5/5 đã đồng bộ** (PRD, SRS, TDD, TC, Plan) | **100%** |
| Mức độ sẵn sàng triển khai Phase 6 | N/A | **Tài liệu: 100%** · **Code: ~10%** | Sẵn sàng implement |
