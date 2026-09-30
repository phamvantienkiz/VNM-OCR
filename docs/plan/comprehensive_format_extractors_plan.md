# Kế Hoạch Triển Khai Phase 6: Comprehensive Format Extractors & Explicit Endpoints

## 1. Bối cảnh
Theo báo cáo nghiên cứu kỹ thuật `docs/research/smart_pdf_classification_and_hybrid_extraction.md`, hệ thống cần cung cấp các **Explicit Dedicated Endpoints** cho từng loại định dạng và ngôn ngữ tài liệu, thay vì chỉ điều hướng cơ bản giữa Fast Path và Heavy Path. Điều này giúp tối ưu hóa phần cứng, tránh kích hoạt các mô hình AI/GPU khi không cần thiết, và chuyên biệt hóa chất lượng bóc tách.

## 2. Mục Tiêu Phase 6
- Xây dựng kiến trúc Extractor Pattern qua Interface `BaseExtractor`.
- Triển khai 4 loại Extractor:
  1. `NativePDFExtractor`: Bóc tách trực tiếp text vector, không qua xử lý ảnh ($< 50ms$).
  2. `DoclingUniversalExtractor`: Chuyên xử lý `.docx`, `.xlsx`, `.pptx`, HTML (sử dụng thư viện office converter nhẹ, tắt OCR ngầm).
  3. `PaddleOCRExtractor`: Hỗ trợ cho tài liệu tiếng Anh chuẩn, paper phức tạp, công thức Toán học (chuẩn bị cho PaddleOCR-VL).
  4. `VNMOCRExtractor`: Wrapper chuẩn hóa cho pipeline tiếng Việt (DLA + TSR + VietOCR Seq2Seq).
- Xây dựng logic điều phối thông minh trong `UniversalDocumentDispatcher` xử lý phân tầng ngôn ngữ và cờ telemetry (`is_vector_recovery`, `requires_image_input`).
- Xây dựng Router độc lập cho `extract`.

## 3. Cấu trúc thư mục mới
```text
backend/app/
├── api/v1/endpoints/
│   └── extract.py              # Các explicit endpoints
├── services/extractors/
│   ├── __init__.py
│   ├── base.py                 # BaseExtractor interface
│   ├── native.py               # NativePDFExtractor
│   ├── docling.py              # DoclingUniversalExtractor
│   ├── paddle.py               # PaddleOCRExtractor
│   └── vnm.py                  # VNMOCRExtractor
```

## 4. Chi tiết Công việc
### Task 1: Định nghĩa Interface & Cập nhật Router
- Cấu trúc `BaseExtractor` gồm phương thức `extract(file_input, **kwargs)` trả về `DocumentExtractionResponse`.
- Bổ sung `extract.py` vào `router.py`.

### Task 2: Cài đặt Native & VNM Extractor
- Đưa Fast Path hiện có vào `NativePDFExtractor`.
- Đưa luồng ONNX hiện tại vào `VNMOCRExtractor`.

### Task 3: Cài đặt Stub/Integration cho Docling & PaddleOCR
- Mặc dù hệ thống giới hạn phần cứng, thiết lập `DoclingUniversalExtractor` bọc thư viện xử lý office nhẹ (không kéo theo easyocr/pytorch trừ khi được chọn explicit). Tạm thời cung cấp integration thô (sẽ fallback hoặc raise nếu thư viện không khả dụng để tuân thủ rule không mock data nhưng vẫn không quá tải).
- Tương tự cho `PaddleOCRExtractor`.

### Task 4: Hoàn thiện UniversalDocumentDispatcher
- Đọc kết quả từ `SmartPDFInspector` (`DIGITAL_DOCUMENT`, `SCANNED_DOCUMENT`, `CORRUPTED_VECTOR`, `COMPLEX_DOCUMENT`).
- Gọi đúng Extractor tương ứng.

## 5. Ràng buộc Kỹ thuật (Constraints)
- Cập nhật file requirements/`pyproject.toml` nhóm `[extractors]` một cách tối ưu. Không force install trên root environment.
- Mọi xử lý phải qua `StreamingUploadGuardMiddleware` và kiểm soát bằng `ocr_semaphore`.
# System Design & Implementation Plan: Comprehensive Format Extractors (Phase 6)

## 1. Architectural Overview & Context

Hệ thống bóc tách tài liệu VNM-OCR cần xử lý đa dạng các định dạng đầu vào (PDF số hóa, PDF scan, Word, Excel, Paper Khoa học, File lỗi font) với độ chính xác cao nhất mà vẫn tuân thủ nghiêm ngặt **Memory Budget** (2GB Soft Limit, 3.5GB Hard Limit). 

Để giải quyết bài toán này, kiến trúc được thiết kế theo mẫu **Strategy Pattern** qua các **Extractors** độc lập, kết hợp với bộ định tuyến thông minh (Smart Router) UniversalDocumentDispatcher.

### 1.1. Data Flow & Communication
1. **Client** gọi API tới các Explicit Endpoints (ví dụ /extract/native/pdf) hoặc endpoint tự động /extract/auto.
2. **API Layer (Controller)** tiếp nhận yêu cầu, kiểm tra Middleware (UploadGuard, MemoryMonitor) và chuyển stream (SpooledTemporaryFile) cho Service Layer.
3. **Service Layer (Dispatcher)** sử dụng SmartPDFInspector để phân tích (nếu gọi auto) và chọn Extractor phù hợp.
4. **Extractor (Strategy)** thực thi logic bóc tách chuyên biệt (không nạp model thừa) và trả về DocumentExtractionResponse thống nhất.

## 2. API Surface Summary (API Design Patterns)

Hệ thống cung cấp một API Surface tường minh (Explicit Endpoints) theo nguyên tắc RESTful.

### 2.1. Endpoints

| Method | Path | Description | Notes |
|---|---|---|---|
| POST | /api/v1/extract/auto | Tự động phân loại & bóc tách | Khuyên dùng cho luồng RAG chung. Trả về pipeline_used trong metadata. |
| POST | /api/v1/extract/native/pdf | Bóc tách text vector siêu tốc | Chỉ dùng cho PDF số hóa (DIGITAL_DOCUMENT), < 50ms. |
| POST | /api/v1/extract/docling | Xử lý file Office & HTML | Dùng cho .docx, .xlsx, .pptx. Chặn OCR ngầm để giảm RAM. |
| POST | /api/v1/extract/paddle/ocr | Trích xuất tiếng Anh / Quốc tế | PaddleOCR (PP-OCRv6) tối ưu cho tiếng Anh. |
| POST | /api/v1/extract/paddle/complex-vlm | Trích xuất Paper / Math | Kích hoạt VLM cho công thức LaTeX và Table lồng. Chịu Timeout dài hơn. |
| POST | /api/v1/extract/vnm | Trích xuất chuẩn tiếng Việt | Sử dụng luồng ONNX hiện tại (DBNet + YOLOv10 + YOLOv8 + VietOCR). |

### 2.2. Data Contracts
Tất cả các endpoints trên đều nhận chung một form data (UploadFile, extract_tables, esolution) và trả về chung một cấu trúc chuẩn DocumentExtractionResponse.
- Bổ sung vào metadata Response:
  - equires_image_input (bool): Engine có yêu cầu render ảnh hay không (VNM, Paddle).
  - is_vector_recovery (bool): Đánh dấu file số hóa bị lỗi font/CMap phải rasterize.
  - pipeline_used (str): Tên của extractor đã thực thi.

## 3. Component & Directory Structure (FastAPI Scaffold)

Tuân thủ nguyên tắc Clean Architecture của astapi-backend-scaffold: Không nhét logic vào API Controller, tách biệt Service và Extractor.

`	ext
backend/app/
├── api/v1/endpoints/
│   └── extract.py              # Controller: Chỉ chứa định nghĩa HTTP Route, gọi Service.
├── services/extractors/
│   ├── __init__.py
│   ├── base.py                 # (Interface) class BaseExtractor: def extract(file_input)
│   ├── native.py               # (Strategy) class NativePDFExtractor(BaseExtractor)
│   ├── docling.py              # (Strategy) class DoclingUniversalExtractor(BaseExtractor)
│   ├── paddle.py               # (Strategy) class PaddleOCRExtractor(BaseExtractor)
│   └── vnm.py                  # (Strategy) class VNMOCRExtractor(BaseExtractor)
└── services/
    └── dispatcher.py           # (Orchestrator) class UniversalDocumentDispatcher
`

## 4. Implementation Steps (Phase 6 Tasks)

### Task 1: Định nghĩa Interface & Tái cấu trúc (app/services/extractors/base.py)
- Khai báo BaseExtractor interface sử dụng bc.ABC. Yêu cầu mọi Extractor tuân thủ def extract(file_input: BinaryIO, **kwargs) -> DocumentExtractionResponse.
- Bổ sung các Exception chung trong pp/exceptions/.

### Task 2: Phát triển NativePDFExtractor & VNMOCRExtractor
- **NativePDFExtractor**: Đưa logic "Fast Path" hiện đang nằm lẫn trong DocumentService sang Extractor này. Sử dụng pdfplumber để trích xuất text trực tiếp. Peak RAM < 200MB.
- **VNMOCRExtractor**: Gọi hàm extract_document của DocumentService để chạy luồng ONNX. Quản lý timeout chặt chẽ.

### Task 3: Phát triển Integration cho Docling & PaddleOCR
- Do tính chất nặng của thư viện, việc cài đặt docling và paddleocr sẽ là Optional [extractors]. 
- Extractor sẽ dùng importlib để kiểm tra: nếu thư viện không tồn tại, trả về lỗi HTTP 501 Not Implemented kèm hướng dẫn chạy pip install .[extractors]. Tuân thủ nguyên tắc **Không dùng Mock Data**.

### Task 4: Cập nhật Dispatcher & API Layer
- Chuyển UniversalDocumentDispatcher thành Factory/Router pattern, nhận input và trả về đúng instance của BaseExtractor dựa vào SmartPDFInspector.classify_document().
- Thêm cờ equires_image_input và is_vector_recovery trong metadata.
- Triển khai extract.py chứa 6 endpoints kể trên. Cấu hình Semaphore hợp lý.

## 5. Ràng buộc Tối ưu hóa & Trade-offs
- **Dependencies Isolation**: Không force người dùng cài bộ thư viện nặng 5GB (Paddle/Docling) trừ khi họ chủ động cài [extractors].
- **Memory Retention**: Mỗi Extractor phải gọi orce_garbage_collection_and_trim() sau khi xong việc để đảm bảo RAM luôn được thu hồi.
- **Backpressure**: Middleware StreamingUploadGuardMiddleware tiếp tục chặn file > 50MB cho toàn bộ các endpoint mới.
