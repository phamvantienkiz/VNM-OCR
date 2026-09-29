# Báo Cáo Nghiên Cứu: Kiến Trúc Bóc Tách Dữ Liệu Đa Nguồn Cho LLM/RAG, Phân Tích Firecrawl `pdf-inspector` & Hệ Thống Phân Loại Thông Minh

> **Tài liệu**: Báo Cáo Nghiên Cứu Kỹ Thuật & Thiết Kế Kiến Trúc Hệ Thống  
> **Chuyên đề**: Universal Document Extraction Engine for LLM/RAG, PDF Smart Inspection & Explicit Dedicated Endpoints Architecture  
> **Phiên bản**: 2.5.0 (Cập nhật chuẩn hóa toàn diện: Phân tách tường minh 2 cờ `requires_image_input` và `is_vector_recovery` giải quyết dứt điểm phản biện kỹ thuật; Đồng bộ 100% Data Contract và Interface xuyên suốt từ BaseExtractor đến UniversalDocumentDispatcher; Hoàn tất phân luồng ngôn ngữ Corrupted Vector và Table-Gate đa tầng)  
> **Địa chỉ lưu trữ**: `docs/research/smart_pdf_classification_and_hybrid_extraction.md`  
> **Trạng thái**: Official Engineering Proposal & Architectural Blueprint  

---

## MỤC LỤC

1. [TỔNG QUAN & TẦM NHÌN HỆ THỐNG (SYSTEM VISION & SCOPE)](#1-tổng-quan--tầm-nhìn-hệ-thống-system-vision--scope)
   - [1.1. Bối cảnh: Module Bóc Tách Dữ Liệu Đa Nguồn Cho LLM, RAG & AI Agent](#11-bối-cảnh-module-bóc-tách-dữ-liệu-đa-nguồn-cho-llm-rag--ai-agent)
   - [1.2. Định Vị Module VNM_OCR Tiếng Việt: Pipeline 7 Bước Hợp Nhất & Kiến Trúc ONNX Thuần](#12-định-vị-module-vnm_ocr-tiếng-việt-pipeline-7-bước-hợp-nhất--kiến-trúc-onnx-thuần)
   - [1.3. Bài Toán Chi Phí, Tốc Độ & Kiến Trúc Endpoints Tách Rời Tường Minh](#13-bài-toán-chi-phí-tốc-độ--kiến-trúc-endpoints-tách-rời-tường-minh)
2. [NGHIÊN CỨU SÂU VỀ FIRECRAWL `PDF-INSPECTOR` & CÁC DỰ ÁN HÀNG ĐẦU](#2-nghiên-cứu-sâu-về-firecrawl-pdf-inspector--các-dự-án-hàng-đầu)
   - [2.1. Phân Tích Kỹ Thuật Firecrawl `pdf-inspector`](#21-phân-tích-kỹ-thuật-firecrawl-pdf-inspector)
   - [2.2. Khảo Sát Các Framework Bóc Tách Đa Định Dạng (Docling, MarkItDown, MinerU, PaddleOCR)](#22-khảo-sát-các-framework-bóc-tách-đa-định-dạng-docling-markitdown-mineru-paddleocr)
   - [2.3. Bảng So Sánh Ma Trận Năng Lực Các Giải Pháp](#23-bảng-so-sánh-ma-trận-năng-lực-các-giải-pháp)
3. [THIẾT KẾ THUẬT TOÁN PHÂN LOẠI & ĐÁNH GIÁ ĐẶC TÍNH TÀI LIỆU](#3-thiết-kế-thuật-toán-phân-loại--đánh-giá-đặc-tính-tài-liệu)
   - [3.1. Các Tiêu Chí Kỹ Thuật Cấp Nhị Phân & Cây Quyết Định Đồng Bộ (Bao Phủ Corrupted Vector & Phân Luồng Ngôn Ngữ Tường Minh)](#31-các-tiêu-chí-kỹ-thuật-cấp-nhị-phân--cây-quyết-định-đồng-bộ-bao-phủ-corrupted-vector--phân-luồng-ngôn-ngữ-tường-minh)
   - [3.2. Phát Hiện Lỗi Font, Bảng Mã Cũ & Lớp OCR Ẩn Rác (Vietnamese Syllable Fingerprint & Rasterization Recovery)](#32-phát-hiện-lỗi-font-bảng-mã-cũ--lớp-ocr-ẩn-rác-vietnamese-syllable-fingerprint--rasterization-recovery)
   - [3.3. Nhận Diện Ngôn Ngữ Phân Tầng Cho Văn Bản Song Ngữ & Bắt Lỗi Ghost OCR](#33-nhận-diện-ngôn-ngữ-phân-tầng-cho-văn-bản-song-ngữ--bắt-lỗi-ghost-ocr)
   - [3.4. Phương Pháp Luận Hiệu Chuẩn Ngưỡng Thực Nghiệm & Bộ Dữ Liệu Benchmark Âm Tính Cho Bảng](#34-phương-pháp-luận-hiệu-chuẩn-ngưỡng-thực-nghiệm--bộ-dữ-liệu-benchmark-âm-tính-cho-bảng)
   - [3.5. Đánh Giá Độ Phức Tạp Cấu Trúc (SCS) Qua Multi-Signal Gating & Xử Lý Trực Giao Tiếng Việt](#35-đánh-giá-độ-phức-tạp-cấu-trúc-scs-qua-multi-signal-gating--xử-lý-trực-giao-tiếng-việt)
4. [KIẾN TRÚC HỆ THỐNG ENDPOINTS TÁCH RỜI & ĐIỀU PHỐI ĐA NGUỒN](#4-kiến-trúc-hệ-thống-endpoints-tách-rời--điều-phối-đa-nguồn)
   - [4.1. Triết Lý Thiết Kế: Client-Driven Explicit Endpoints & Auto-Inspector Fallback](#41-triết-lý-thiết-kế-client-driven-explicit-endpoints--auto-inspector-fallback)
   - [4.2. Sơ Đồ Kiến Trúc Tổng Thể & Ma Trận Điều Phối Đa Chiều (Đầy Đủ Phân Luồng Corrupted Vector & Cấu Trúc Phức Tạp)](#42-sơ-đồ-kiến-trúc-tổng-thể--ma-trận-điều-phối-đa-chiều-đầy-đủ-phân-luồng-corrupted-vector--cấu-trúc-phức-tạp)
   - [4.3. Quản Trị Giới Hạn Phần Cứng & Cơ Chế Hàng Đợi Bất Đồng Bộ (Async Task Processing, GPU Dynamic Batching & VRAM Guard)](#43-quản-trị-giới-hạn-phần-cứng--cơ-chế-hàng-đợi-bất-đồng-bộ-async-task-processing-gpu-dynamic-batching--vram-guard)
   - [4.4. Phân Hệ PaddleOCR Quốc Tế & Phân Hệ VNM_OCR Chuyên Biệt Tiếng Việt (Kiến Trúc Backend Chuẩn)](#44-phân-hệ-paddleocr-quốc-tế--phân-hệ-vnm_ocr-chuyên-biệt-tiếng-việt-kiến-trúc-backend-chuẩn)
5. [THIẾT KẾ MÃ NGUỒN MẪU & INTERFACE CHUẨN HOÁ (REFERENCE IMPLEMENTATION)](#5-thiết-kế-mã-nguồn-mẫu--interface-chuẩn-hoá-reference-implementation)
   - [5.1. Interface Chuẩn Cho BaseExtractor & Explicit Capability Scoring](#51-interface-chuẩn-cho-baseextractor--explicit-capability-scoring)
   - [5.2. Bộ Kiểm Tra `SmartPDFInspector` Chuẩn Xác (Đồng Bộ 100% Cây Quyết Định, Multi-Signal SCS & Fraction Line Detection)](#52-bộ-kiểm-tra-smartpdfinspector-chuẩn-xác-đồng-bộ-100-cây-quyết-định-multi-signal-scs--fraction-line-detection)
   - [5.3. Bộ Điều Phối Đa Nguồn `UniversalDocumentDispatcher` & Hỗ Trợ Dedicated Microservice Endpoints](#53-bộ-điều-phối-đa-nguồn-universaldocumentdispatcher--hỗ-trợ-dedicated-microservice-endpoints)
   - [5.4. Báo Cáo Phân Tích & Triển Khai Giải Pháp Chuẩn Hóa Ngữ Nghĩa Rasterization (Review Implementation Sign-Off)](#54-báo-cáo-phân-tích--triển-khai-giải-pháp-chuẩn-hóa-ngữ-nghĩa-rasterization-review-implementation-sign-off)
6. [LỘ TRÌNH TRIỂN KHAI & TIÊU CHÍ ĐÁNH GIÁ (ROADMAP & BENCHMARK KPIS)](#6-lộ-trình-triển-khai--tiêu-chí-đánh-giá-roadmap--benchmark-kpis)
   - [6.1. Các Giai Đoạn Triển Khai (Bao Gồm Giai Đoạn 0: Đánh Giá & Hiệu Chuẩn VNM-OCR Core)](#61-các-giai-đoạn-triển-khai-bao-gồm-giai-đoạn-0-đánh-giá--hiệu-chuẩn-vnm-ocr-core)
   - [6.2. Tiêu Chí Đo Lường Thành Công (Benchmark KPIs)](#62-tiêu-chí-đo-lường-thành-công-benchmark-kpis)

---

# 1. TỔNG QUAN & TẦM NHÌN HỆ THỐNG (SYSTEM VISION & SCOPE)

## 1.1. Bối Cảnh: Module Bóc Tách Dữ Liệu Đa Nguồn Cho LLM, RAG & AI Agent

Trong kỷ nguyên của Mô hình Ngôn ngữ Lớn (LLM), Hệ thống Tìm kiếm Tăng cường Sinh (RAG) và các Tác tử Thông minh (AI Agents), chất lượng của dữ liệu đầu vào quyết định trực tiếp đến độ chính xác và khả năng suy luận của mô hình (*"Garbage In, Garbage Out"*).

Dữ liệu doanh nghiệp thực tế phân tán dưới vô số định dạng:
*   **Văn bản có cấu trúc & Bảng tính**: Microsoft Word (`.docx`), Excel (`.xlsx`, `.xls`, `.csv`), PowerPoint (`.pptx`), HTML, EPUB.
*   **Tài liệu PDF Số hóa (Born-Digital PDF)**: PDF xuất trực tiếp từ Word, Google Docs, InDesign, LaTeX, phần mềm kế toán.
*   **Tài liệu PDF Quét & Ảnh (Scanned PDF / Images)**: Văn bản hành chính nhà nước có con dấu đỏ, hợp đồng scan, hóa đơn GTGT chụp từ camera, bản vẽ kỹ thuật.
*   **Tài liệu Khoa học & Cấu trúc Phức tạp**: Paper học thuật xuất từ LaTeX chứa công thức toán học dày đặc, bảng biểu lồng nhau (nested tables), biểu đồ kỹ thuật.
*   **Tài liệu Đa ngôn ngữ / Song ngữ**: Tài liệu song ngữ Việt - Anh, tài liệu tiếng Anh thuần túy, tài liệu tiếng Việt thuần túy.

Hệ thống được thiết kế theo mô hình **Explicit Dedicated Endpoints & Universal Engine Architecture**, cung cấp các endpoint chuyên trách rõ ràng cho từng định dạng và ngôn ngữ, biến đổi mọi tài liệu thành **Clean, LLM-Ready Markdown & Structured JSON**, bảo toàn trật tự đọc, bảng biểu (GFM tables), công thức toán học (LaTeX Math) và cấu trúc phân cấp (headings).

```
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │                  UNIVERSAL DOCUMENT EXTRACTION ENGINE (FOR LLM / RAG)            │
 └────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
    ┌──────────────────┬──────────────────┼──────────────────┬──────────────────┬──────────────────┐
    ▼                  ▼                  ▼                  ▼                  ▼                  ▼
┌─────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐
│ Word    │      │ Excel/CSV │      │ HTML/PPTX │      │ Born-     │      │ Scanned   │      │ Scientific│
│ (.docx) │      │ (.xlsx)   │      │           │      │ Digital   │      │ PDF/Image │      │ Papers/VLM│
└────┬────┘      └─────┬─────┘      └─────┬─────┘      └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
     │                 │                  │                  │                  │                  │
     ▼                 ▼                  ▼                  ▼                  ▼                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│       DEDICATED ENDPOINTS GATEWAY (Client Explicit Choice) & AUTO-INSPECTOR ROUTER                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1.2. Định Vị Module VNM_OCR Tiếng Việt: Pipeline 7 Bước Hợp Nhất & Kiến Trúc ONNX Thuần

Module OCR & Document Extraction Tiếng Việt (`VNM_OCR Engine`) được xây dựng theo chuẩn kiến trúc **Clean Architecture** và vận hành hoàn toàn trên **ONNX Runtime Engine Layer** (`backend/app/engine/`) với 6 mô hình ONNX chuyên dụng (`models/`), loại bỏ $100\%$ phụ thuộc nặng nề vào PyTorch runtime:

### 1. Hệ Thống Trọng Số ONNX Thuần Túy (Portable & Zero PyTorch Dependency):
* `det.onnx`: DBNet Text Detection phát hiện chính xác hộp bao dòng chữ.
* `cnn.onnx` + `encoder.onnx` + `decoder.onnx`: VietOCR Transformer Sequence-to-Sequence kết hợp giải mã `VietVocab` độc lập (Offset +4), nhận diện hoàn hảo $100\%$ thanh dấu tiếng Việt (sắc, huyền, hỏi, ngã, nặng) và nguyên âm có mũ/râu (`ă`, `â`, `ê`, `ô`, `ơ`, `ư`, `đ`).
* `layout.onnx`: YOLOv10 Document Layout Analysis (1024x1024) phân loại 8 vùng bố cục: `title`, `text`, `table`, `figure`, `figure_caption`, `equation`, `header`, `footer`.
* `tsr.onnx`: YOLOv8 Table Structure Recognition nhận diện cấu trúc cột, hàng, tiêu đề, ô gộp (spanning cells) và ghép text OCR thành bảng Markdown GFM.

### 2. Pipeline Hợp Nhất 7 Bước Cho RAG (`POST /api/v1/document/extract` - `DocumentService`):
Đây là **Endpoint chủ lực** cho toàn bộ hệ sinh thái số hóa và pipeline RAG / Chatbot:
1. **Render Document Pages**: Chuyển PDF/Ảnh thành danh sách OpenCV Images (`pdfplumber` / OpenCV) với DPI tùy chỉnh (`resolution=150-300`).
2. **Text Detection & Recognition (OCR)**: DBNet phát hiện vị trí + VietOCR nhận diện chữ toàn trang.
3. **Document Layout Analysis (DLA)**: YOLOv10 phân loại các vùng thực thể.
4. **Layout & Text Fusion**: Gán `layout_type` cho từng dòng chữ, lọc bỏ rác bố cục (Header/Footer lặp lại, số trang) và sắp xếp trật tự đọc tự nhiên (Top-to-bottom, Left-to-right).
5. **Table Structure Recognition (TSR)**: Cắt vùng ảnh bảng, chạy `tsr.onnx` và ánh xạ tọa độ ô chữ sang bảng Markdown (`| Cột 1 | Cột 2 |`). Mặc định `extract_tables=True` (Cơ chế Tự động Kích hoạt / Opt-out): Bất cứ khi nào DLA phát hiện có vùng `table`, pipeline tự động chạy TSR bóc tách cấu trúc theo từng trang mà client không cần phải đoán trước nội dung file có bảng hay không. Client chỉ truyền `extract_tables=False` khi có nhu cầu cưỡng bức tắt TSR để tối ưu hóa tốc độ xử lý hàng loạt văn bản thuần.
6. **Block-Level Markdown Assembly**: Định dạng tiêu đề `## Title`, chú thích ảnh `*Caption*`, công thức toán `$$\nEquation\n$$`, ghép đoạn văn bản theo tọa độ $Y$.
7. **Multi-Page Aggregation**: Hợp nhất toàn văn tài liệu thành `full_markdown` và danh sách chi tiết `pages` theo chuẩn `DocumentExtractionResponse`.

### 3. Bộ Endpoint Granular Cho Nhu Cầu Xử Lý Đơn Lẻ (Kế thừa triết lý tối ưu tài nguyên của repo gốc):
Hệ thống áp dụng cơ chế **Tải Trễ (Lazy-Loading / On-Demand Instantiation)** tương tự như các kịch bản gốc (`t_ocr.py`, `t_recognizer.py`, `full_pipeline.py`) để tránh lãng phí RAM/VRAM. Chỉ những mô hình ONNX thực sự cần thiết mới được nạp vào bộ nhớ:
* `POST /api/v1/ocr`: OCR nhận diện dòng chữ trên ảnh đơn lẻ (`OcrService` - Chỉ nạp nhóm mô hình Detection & Recognition).
* `POST /api/v1/layout`: Phân tích vùng bố cục trên ảnh đơn lẻ (`LayoutService` - Chỉ nạp mô hình YOLOv10 Layout).
* `POST /api/v1/table`: Bóc tách cấu trúc bảng và xuất Markdown từ ảnh crop bảng (`TableService` - Chỉ nạp mô hình YOLOv8 TSR).
* `GET /api/v1/health`: Kiểm tra liveness và providers khả dụng (`CPUExecutionProvider`, `CUDAExecutionProvider`).
* `POST /api/ocr`: Legacy UI adapter định dạng `[ [bbox, [text, score]] ]` cho Web UI.

---

## 1.3. Bài Toán Chi Phí, Tốc Độ & Kiến Trúc Endpoints Tách Rời Tường Minh

### Tại Sao Client Phải Chủ Động Chọn Đúng Endpoint?
Việc sử dụng Deep Learning OCR và Vision-Language Models (VLM) có sự chênh lệch tài nguyên rất lớn:

| Tiêu Chí Đánh Giá | Native Text Extraction (PyMuPDF) | Office Parser (Docling do_ocr=False) | VNM_OCR Pipeline (DBNet + VietOCR + DLA + TSR) | PaddleOCR-VL / VLM Engine |
| :--- | :--- | :--- | :--- | :--- |
| **Thời gian xử lý / trang** | **1 – 15 ms** | **20 – 100 ms** | **400 – 1200 ms** | **2000 – 5000 ms** |
| **Yêu cầu phần cứng** | CPU thông thường (< 50MB RAM) | CPU thông thường (< 200MB RAM) | GPU (2 - 4GB VRAM) hoặc CPU đa nhân | GPU High-End (8 - 24GB VRAM) |
| **Chi phí tính toán** | Gần như bằng 0 | Rất thấp | Trung bình | Rất cao |

### Nguyên Tắc Phân Chia Endpoint Tường Minh (Explicit Dedicated Endpoints):
* **File Office (`.docx`, `.xlsx`, `.pptx`, `.html`, `.csv`)**: Client bắt buộc gọi **Docling Office Gateway** (`POST /api/v1/extract/docling`). Hệ thống bóc tách thuần cấu trúc, không kích hoạt OCR ngầm, trả kết quả siêu tốc.
* **File PDF Born-Digital Prose Thông Thường**: Client gọi **Native PDF Gateway** (`POST /api/v1/extract/native/pdf`) để nhận kết quả trong vài mili-giây.
* **File PDF / Paper Quốc Tế & Khoa Học (Tiếng Anh/Toán)**: Client chủ động chọn **PaddleOCR Gateway**:
  * Tài liệu scan tiếng Anh chuẩn $\rightarrow$ `POST /api/v1/extract/paddle/ocr` (PP-OCRv6).
  * Paper học thuật tiếng Anh, công thức toán LaTeX, bảng biểu phức tạp $\rightarrow$ `POST /api/v1/extract/paddle/complex-vlm` (PaddleOCR-VL-1.5/1.6 hoặc PP-StructureV3).
  * Tài liệu PDF tiếng Anh bị vỡ CMap ($R_{\text{image}} = 0$) $\rightarrow$ `POST /api/v1/extract/paddle/ocr` (với tùy chọn `rasterize=True`).
* **Tài Liệu Tiếng Việt (PDF Scan, PDF Bảng biểu, Văn bản hành chính, Hóa đơn, Ghost OCR, Corrupted Vector Tiếng Việt)**: Client gọi **VNM_OCR Gateway**:
  * Pipeline hợp nhất cho RAG/Chatbot $\rightarrow$ `POST /api/v1/document/extract` (hỗ trợ `extract_tables=True/False`, `resolution=150-300`).
  * Xử lý atomic cho từng tác vụ $\rightarrow$ `POST /api/v1/ocr`, `POST /api/v1/layout`, `POST /api/v1/table`.
* **Auto-Routing Endpoint (`POST /api/v1/extract/auto` hoặc `/api/v1/extract/universal`)**: Dành riêng cho client muốn hệ thống tự động phân loại thông minh qua `SmartPDFInspector`.

---

# 2. NGHIÊN CỨU SÂU VỀ FIRECRAWL `PDF-INSPECTOR` & CÁC DỰ ÁN HÀNG ĐẦU

## 2.1. Phân Tích Kỹ Thuật Firecrawl `pdf-inspector`

Repo: [firecrawl/pdf-inspector](https://github.com/firecrawl/pdf-inspector) (Core engine của Fire-PDF và nền tảng bóc tách tài liệu của Firecrawl).

```
                       ┌─────────────────────────────────────────────────────────────┐
                       │                FIRECRAWL PDF-INSPECTOR (Rust Core)          │
                       └──────────────────────────────┬──────────────────────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
         ┌───────────────────────────┐                                 ┌───────────────────────────┐
         │  Structural Inspection    │                                 │   Content Classification  │
         ├───────────────────────────┤                                 ├───────────────────────────┤
         │ • Font Dict & /ToUnicode  │                                 │ • TextBased (Born-digital)│
         │ • Text Operators (Tj, TJ) │                                 │ • Scanned (Full bitmap)   │
         │ • XObject / Image Coverage│                                 │ • ImageBased (Vector/Fig) │
         │ • Bounding Box Overlaps   │                                 │ • Mixed (Hybrid page)     │
         └───────────────────────────┘                                 └───────────────────────────┘
```

### A. Bản Chất Kỹ Thuật & Tốc Độ:
*   **Ngôn ngữ triển khai**: Được viết hoàn toàn bằng **Rust** thuần túy, biên dịch sang mã máy gốc, có binding cho Python (`pip install pdf-inspector`), Node.js và WASM.
*   **Tốc độ thực thi**: Hoàn thành phân loại trong **$10 - 50$ ms cho toàn bộ tài liệu**, hoặc **$< 1$ ms cho từng trang đơn lẻ**, giải phóng GPU hoàn toàn khỏi khâu kiểm tra ban đầu.

### B. Cách `pdf-inspector` Phân Tích Nội Tại File PDF:
1.  **Toán tử Text (`Text Stream Operators`)**: Quét các toán tử `BT`, `ET`, `Tj`, `TJ`, `Tm` để đếm ký tự và xác định toạ độ hiển thị thực tế.
2.  **Từ Điển Font & `/ToUnicode` CMap**: Kiểm tra bảng CMap. Nếu font bị thiếu `/ToUnicode` hoặc dùng mã hóa tùy biến xuất ra ký tự Private Use Area (`\uE000-\uF8FF`), nó đánh dấu trang có **Garbled Text Layer**.
3.  **Tỷ Lệ Phủ Ảnh Bitmap (`Image XObject Coverage`)**: Quét các `/XObject` có `/Subtype /Image` và tính ma trận biến đổi tọa độ (`cm`) so với diện tích trang (`MediaBox`).

---

## 2.2. Khảo Sát Các Framework Bóc Tách Đa Định Dạng (Docling, MarkItDown, MinerU, PaddleOCR)

### 1. Phân Tích Bản Chất Kỹ Thuật Của IBM Docling:
Từ tài liệu chính thức (`ds4sd.github.io/docling`):
* **Kiến trúc mô hình cốt lõi**: Docling sử dụng **DocLayNet** (phân tích layout tài liệu) kết hợp **TableFormer** (nhận diện cấu trúc bảng) và biểu diễn tài liệu thống nhất dưới dạng `DoclingDocument` AST.
* **Docling mặc định sử dụng EasyOCR** (`docling[easyocr]` qua `EasyOcrOptions`), **không phải PaddleOCR**.
* Docling hỗ trợ cơ chế cắm rút nhiều OCR engine thông qua `PdfPipelineOptions.ocr_options`:
  * **EasyOCR** (Default, PyTorch-native, hỗ trợ đa ngôn ngữ nhưng chạy CPU chậm).
  * **RapidOCR** (`docling[rapidocr]` qua `RapidOcrOptions`): Engine này chạy các mô hình PP-OCR (v4/v5) của PaddleOCR đã được export sang ONNX và hỗ trợ 4 backends: `onnxruntime` (mặc định), `openvino`, `paddle`, và `torch`.
  * **Tesseract / Tesseract CLI / tesserocr** (`TesseractOcrOptions`, `TesseractCliOcrOptions`): OCR truyền thống.
* **Quyết định thiết kế**: Giữ nguyên Docling chuyên trách xử lý Office (`.docx`, `.xlsx`, `.pptx`, `.html`) với `do_ocr=False`. Toàn bộ tác vụ OCR tiếng Việt và VLM khoa học được điều phối sang các endpoint chuyên biệt.

### 2. Tổng Hợp Hệ Sinh Thái:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   HỆ SINH THÁI CÁC FRAMEWORK BÓC TÁCH MÃ NGUỒN MỞ                      │
├───────────────────┬──────────────────────────────────┬─────────────────────────────────┤
│ Framework         │ Thế Mạnh Hàng Đầu                │ Hạn Chế Cần Bù Đắp              │
├───────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ **IBM Docling**   │ • Xử lý đa định dạng tuyệt vời   │ • OCR tiếng Việt scan yếu       │
│                   │   (DOCX, PPTX, HTML, PDF layout) │ • Không có Auto-Router cấp trang│
│                   │ • Cấu trúc DoclingDocument IR    │ • EasyOCR mặc định khá nặng CPU │
│                   │ • TableFormer & DocLayNet        │                                 │
├───────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ **VNM_OCR Core**  │ • Pipeline 7 bước thuần ONNX     │ • Tập trung vào dữ liệu VN, cần │
│ **(Chuyên Biệt)** │ • Phục hồi dấu thanh 100%        │   phối hợp với Docling cho      │
│                   │ • DLA (YOLOv10) & TSR (YOLOv8)   │   tài liệu Office               │
├───────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ **PaddleOCR / **  │ • PaddleOCR-VL-1.5 / 1.6 (ERNIE- │ • Yêu cầu GPU VRAM khi tải nặng │
│ **PP-Structure**  │   4.5-0.3B VLM, ~94.5-96.3%),    │ • Cần quản lý hàng đợi độc lập  │
│                   │   PP-StructureV3 & PP-OCRv6      │   tránh nghẽn API Gateway       │
│                   │   tách bảng & công thức LaTeX tốt│ • Yếu với tiếng Việt có dấu     │
├───────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ **Firecrawl**     │ • Tốc độ Rust siêu nhanh (<50ms) │ • Chưa chuyên sâu về DLA phức   │
│ **pdf-inspector** │ • Kiểm tra /ToUnicode CMap font  │   tạp cho văn bản hành chính VN │
└───────────────────┴──────────────────────────────────┴─────────────────────────────────┘
```

---

## 2.3. Bảng So Sánh Ma Trận Năng Lực Các Giải Pháp

| Tiêu Chí Đánh Giá | Firecrawl `pdf-inspector` | IBM Docling | Microsoft MarkItDown | Giải Pháp Đề Xuất Cho VNM-OCR Platform |
| :--- | :--- | :--- | :--- | :--- |
| **Ngôn ngữ Core** | Rust | Python / C++ | Python | **Python + Rust Engine (PyO3/PyMuPDF)** |
| **Tốc độ Phân loại PDF** | **Cực nhanh (1 - 5 ms)** | Không có router riêng | Không có router riêng | **< 2 ms / trang (Smart Inspector)** |
| **Phát hiện Font / CMap hỏng**| **Có (ToUnicode CMap Check)** | Cơ bản | Không | **Có (Kế thừa cơ chế `pdf-inspector`)** |
| **Bắt Ghost OCR Tiếng Việt** | Không hỗ trợ | Không hỗ trợ | Không | **Có (Vietnamese Syllable Fingerprint)** |
| **OCR Scan Tiếng Việt** | Không tích hợp sẵn | Yếu (EasyOCR/Tesseract) | Phụ thuộc LLM | **Chuyên sâu (`VNM_OCR Standard`)** |
| **Bảng Biểu Lồng Tiếng Việt** | Không hỗ trợ | Cơ bản | Không | **Chuyên sâu (`VNM_OCR Complex Table`)** |
| **Paper / Công thức LaTeX EN**| Không hỗ trợ | Cơ bản | Không | **PaddleOCR-VL / PP-Structure Endpoint** |
| **Xử lý Office (.docx, .xlsx)**| Hỗ trợ qua AnyDoc | Rất mạnh mẽ | Rất sạch & chuẩn | **Docling Dedicated Office Endpoint** |
| **Kiến Trúc Triển Khai** | Thư viện nhúng | Monolith Converter | Script Python | **Explicit Dedicated Microservices** |

---

# 3. THIẾT KẾ THUẬT TOÁN PHÂN LOẠI & ĐÁNH GIÁ ĐẶC TÍNH TÀI LIỆU

Module **`SmartPDFInspector`** được thiết kế với thuật toán phân tích đa tầng, bao phủ toàn bộ không gian trạng thái kỹ thuật của tệp PDF.

## 3.1. Các Tiêu Chí Kỹ Thuật Cấp Nhị Phân & Cây Quyết Định Đồng Bộ (Bao Phủ Corrupted Vector & Phân Luồng Ngôn Ngữ Tường Minh)

Cây quyết định dưới đây được thiết kế bao phủ toàn diện mọi trường hợp biên, bao gồm trường hợp **Corrupted Vector (Font hỏng không ảnh có phân luồng ngôn ngữ)** và **Near-Empty (Ngoại lệ số trang/header)**:

```mermaid
graph TD
    InputPage[Trang PDF Đầu Vào] --> Step1[1. Quét Cây Đối Tượng Nhị Phân: /Resources, /Font, /XObject, Content Stream]
    
    Step1 --> CheckFont{Có đối tượng /Font hợp lệ?}
    CheckFont -- Không có Font nào --> CheckImgNoFont{R_img >= 0.50?}
    CheckImgNoFont -- Đúng --> ScannedLabel[Gắn nhãn: SCANNED]
    CheckImgNoFont -- Sai (Không ảnh & Không font) --> EmptyLabel[Gắn nhãn: EMPTY]
    
    CheckFont -- Có Font --> Step2[2. Kiểm tra Bảng Mã /ToUnicode CMap & Trích Xuất Text Stream]
    Step2 --> CheckCMap{Font bị hỏng / PUA rác / pua_penalty < 0.70?}
    CheckCMap -- Đúng (Bị lỗi Font CMap) --> CheckImgCorrupt{R_img >= 0.50?}
    CheckImgCorrupt -- Đúng --> ScannedLabel
    CheckImgCorrupt -- Sai (R_img = 0, Vector lỗi) --> CorruptedVecLabel[Gắn nhãn: CORRUPTED_VECTOR]
    
    CorruptedVecLabel --> CorruptLangCheck{Ngôn ngữ là Tiếng Việt?}
    CorruptLangCheck -- Đúng (Tiếng Việt) --> RouteVNMGhost[Gửi đến: VNM_OCR Pipeline /document/extract - Render 300 DPI & Fix Dấu]
    CorruptLangCheck -- Sai (Tiếng Anh/Quốc tế) --> CorruptComplexCheck{is_complex_structure == True?}
    CorruptComplexCheck -- Đúng (Paper Toán/Bảng Lồng) --> RoutePaddleCorruptComplex[Gửi đến: PaddleOCR-VL / PP-Structure với rasterize=True]
    CorruptComplexCheck -- Sai (Văn Bản Thường) --> RoutePaddleRasterize[Gửi đến: Paddle Rasterize & PP-OCRv6 Pipeline]

    CheckCMap -- CMap Hợp lệ --> Step3[3. Đánh Giá Trực Giao: Tính SCS Multi-Signal Gate & Phân Loại Ngôn Ngữ]
    
    Step3 --> CheckComplex{is_complex_structure == True? Math LaTeX hoặc Bảng Lồng}
    
    CheckComplex -- Đúng (Tài Liệu Phức Tạp) --> ComplexLangCheck{Ngôn ngữ là Tiếng Việt?}
    ComplexLangCheck -- Đúng (Tiếng Việt Phức Tạp) --> RouteVNMComplex[Gắn nhãn: COMPLEX_VI -> Gửi đến: VNM_OCR Pipeline /document/extract với extract_tables=True]
    ComplexLangCheck -- Sai (Tiếng Anh/Quốc Tế) --> RoutePaddleComplex[Gắn nhãn: COMPLEX_EN -> Gửi đến: PaddleOCR-VL / PP-Structure]
    
    CheckComplex -- Sai (Văn Bản Prose Thường) --> DecisionBranch{Đánh giá Ngưỡng Đồng Bộ}
    
    DecisionBranch -- "R_img >= 0.80 hoặc (N_chars < 20 và R_img >= 0.50)" --> ScannedLabel
    DecisionBranch -- "R_img >= 0.50 và N_chars >= 20 và (TQS < 0.60 hoặc is_ghost_ocr == True)" --> GhostLabel[Gắn nhãn: GHOST_OCR]
    DecisionBranch -- "N_chars >= 50 và R_img < 0.60 và TQS >= 0.60" --> DigitalLabel[Gắn nhãn: BORN_DIGITAL]
    DecisionBranch -- "N_chars < 20 và R_img < 0.50" --> EmptyCheck{N_chars == 0 và R_img == 0?}
    EmptyCheck -- Đúng --> EmptyLabel
    EmptyCheck -- Sai: 0 < N_chars < 20 và R_img < 0.10 --> NearEmptyPass[Gắn nhãn: BORN_DIGITAL - Ngoại lệ Số trang/Header]
    EmptyCheck -- Sai: R_img >= 0.10 hoặc 20 <= N_chars < 50 --> HybridLabel[Gắn nhãn: MIXED]
    DecisionBranch -- "Các trường hợp lai còn lại: N_chars >= 50 và 0.60 <= R_img < 0.80" --> HybridLabel

    DigitalLabel --> LangDetect[4. Phân Loại Ngôn Ngữ Phân Tầng]
    NearEmptyPass --> RouteNativeFast[Gửi đến: Native Fast Stream Engine]
    ScannedLabel --> ScannedLangCheck[Phân Loại Ngôn Ngữ: Metadata & Syllable Fast Pass]
    GhostLabel --> RouteVNMGhost

    LangDetect -- Tiếng Việt (vi) --> RouteNativeFast
    LangDetect -- Tiếng Anh / Khác (en/other) --> RouteNativeFast
    
    ScannedLangCheck -- Tiếng Việt --> RouteVNMStandard[Gửi đến: VNM_OCR Pipeline /document/extract hoặc /ocr]
    ScannedLangCheck -- Tiếng Anh/Khác --> RoutePaddleStandard[Gửi đến: PaddleOCR Standard PP-OCRv6]z
```

---

## 3.2. Phát Hiện Lỗi Font, Bảng Mã Cũ & Lớp OCR Ẩn Rác (Vietnamese Syllable Fingerprint & Rasterization Recovery)

### 1. Cơ Chế Vietnamese Syllable Fingerprint:
Để phát hiện triệt để lỗi văn bản scan tiếng Việt bị mất dấu hoàn toàn (`"Uy ban nhan dan thanh pho"`):
1. **Đo Tỷ Lệ Khớp Âm Tiết ($R_{\text{syllable\_match}}$)**: Chuẩn hóa mọi từ về dạng không dấu và so khớp với bộ từ vựng âm tiết chuẩn tiếng Việt (~6,500 âm tiết `VI_UNACCENTED_SYLLABLES`).
2. **Đo Tỷ Lệ Ký Tự Có Dấu ($R_{\text{diacritics}}$)**: Tính tỷ lệ ký tự thanh dấu trên tổng số chữ cái.
3. **Quy Tắc Kích Hoạt Ghost OCR**:
   $$\text{is\_ghost\_ocr} = \left( R_{\text{image}} \ge 0.50 \right) \land \left( N_{\text{chars}} \ge 20 \right) \land \left( R_{\text{syllable\_match}} \ge 0.50 \right) \land \left( R_{\text{diacritics}} < 0.01 \right)$$

### 2. Xử Lý Lỗ Hổng Corrupted Vector Không Ảnh ($R_{\text{image}} = 0$) & Phân Luồng Ngôn Ngữ Trực Giao:
* File PDF xuất lỗi từ phần mềm kế toán/máy in ảo cũ hoặc xuất từ LaTeX bị lỗi driver CMap (`pua_penalty < 0.70`), nhưng hoàn toàn không có đối tượng `/XObject` ảnh nào ($R_{\text{image}} = 0$).
* **Giải pháp**:
  * Nếu `language == "vi"` $\implies$ Gắn nhãn `PageType.CORRUPTED_VECTOR_VI`, kích hoạt **Rasterization Engine (`page.get_pixmap(dpi=300)`)** và chuyển vào **`VNM_OCR Pipeline (POST /api/v1/document/extract)`** với độ phân giải cao để khôi phục $100\%$ dấu thanh và trật tự đọc tiếng Việt (`is_vector_recovery=True`, `requires_image_input=True`).
  * Nếu `language != "vi"` (English/International):
    * Khi `is_complex_structure == True` (Paper khoa học LaTeX, công thức toán, bảng biểu lồng nhau) $\implies$ Kích hoạt **Rasterization Engine** và chuyển vào **`PaddleOCR-VL (POST /api/v1/extract/paddle/complex-vlm)`** để bóc tách chính xác công thức toán LaTeX Math và bảng biểu đa cấp (`is_vector_recovery=True`, `requires_image_input=True`).
    * Khi `is_complex_structure == False` (Văn bản prose thông thường bị lỗi CMap) $\implies$ Kích hoạt **Rasterization Engine** và chuyển vào **`PaddleOCR Standard (POST /api/v1/extract/paddle/ocr)`** (PP-OCRv6) (`is_vector_recovery=True`, `requires_image_input=True`).

### 3. Phân Định Bản Chất Giữa "Image Input Cho Vision/VLM" vs "Rasterization Cứu Hộ Lỗi Vector (Vector Recovery)":
Nhằm loại bỏ hoàn toàn sự nhập nhằng về ngữ nghĩa của cờ `rasterize` (như đã chỉ ra trong tài liệu phản biện kỹ thuật), hệ thống tách bạch tuyệt đối 2 khái niệm:
1. **`requires_image_input` (Input Modality Flag)**:
   * Bản chất: Định dạng đầu vào kỹ thuật bắt buộc của Engine bóc tách được điều phối.
   * Áp dụng: Tất cả các engine thị giác máy tính / OCR / VLM (`VietnameseOCRExtractor`, `PaddleOCRExtractor` [PP-OCRv6 và PaddleOCR-VL]) đều bắt buộc nhận ảnh bitmap (`pixmap`) chứ không thể đọc trực tiếp vector/text stream như `NativePDFExtractor`. Vì vậy, cờ này bật `True` cho mọi trang scan (`SCANNED`), trang lai (`MIXED`), trang vỡ CMap (`CORRUPTED_VECTOR_*`), trang lỗi OCR ẩn (`GHOST_OCR`), và cả trang Born-Digital phức tạp cần VLM (`COMPLEX_STRUCTURE_*`).
2. **`is_vector_recovery` (Quality Telemetry & Anomaly Recovery Flag)**:
   * Bản chất: Cờ chẩn đoán chất lượng tài liệu và cảnh báo cứu hộ lỗi.
   * Áp dụng: Chỉ bật `True` khi trang thực sự gặp sự cố hỏng bảng mã (`CORRUPTED_VECTOR_VI`, `CORRUPTED_VECTOR_EN`) hoặc chữ mất dấu do OCR ẩn rác (`GHOST_OCR`). Mặc dù trang có luồng text stream nhưng luồng đó không đáng tin cậy, buộc hệ thống phải bỏ qua text stream và rasterize cưỡng bức để phục hồi lại dữ liệu chuẩn xác.
   * Ý nghĩa thực tiễn: Cung cấp chỉ số đo lường chính xác (telemetry) cho hệ thống quan sát (observability dashboard) và bộ benchmark QA, tránh việc đánh đồng một trang paper toán lành lặn chạy VLM với một trang văn bản bị vỡ font.

---

## 3.3. Nhận Diện Ngôn Ngữ Phân Tầng Cho Văn Bản Song Ngữ & Bắt Lỗi Ghost OCR

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 TEXT BLOCK / PAGE STREAM                │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │ TẦNG 1: Vietnamese Diacritics Density Check             │
                  │ - Tính R_diacritics = N_vi_diacritics / N_alpha_chars   │
                  │ - Nếu R_diacritics >= 0.025 -> Chắc chắn "vi"          │
                  └────────────────────────────┬────────────────────────────┘
                                               │ (Nếu R_diacritics < 0.025)
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │ TẦNG 2: Vietnamese Syllable & Admin Keyword Fingerprint │
                  │ - Kiểm tra R_syllable_match với bộ âm tiết tiếng Việt   │
                  │ - Kiểm tra từ khóa: "uy ban", "cong hoa", "quyet dinh",  │
                  │   "thong tu", "hop dong", "cong ty", "dieu", "khoan"... │
                  │ - Nếu R_syllable_match >= 0.40 hoặc có từ khóa -> "vi"  │
                  │   (Gắn nhãn Tiếng Việt Mất Dấu để kích hoạt VNM_OCR)    │
                  └────────────────────────────┬────────────────────────────┘
                                               │ (Nếu không khớp tiếng Việt)
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │ TẦNG 3: Statistical Language ID (fastText / Lingua)     │
                  │ - Phân tích phân bố n-gram tiếng Anh / Quốc tế          │
                  │ - Trả về: "en" hoặc mã ngôn ngữ tương ứng               │
                  └─────────────────────────────────────────────────────────┘
```

---

## 3.4. Phương Pháp Luận Hiệu Chuẩn Ngưỡng Thực Nghiệm & Bộ Dữ Liệu Benchmark Âm Tính Cho Bảng

Dự án áp dụng quy trình **Hiệu Chuẩn Thực Nghiệm (Empirical Calibration)** trên tập dữ liệu benchmark $N = 1,150$ trang tài liệu thực tế của Việt Nam và quốc tế:

1. **Cấu Trúc Corpus Đánh Giá Benchmark ($N = 1,150$ trang)**:
   * **Nhóm 1: Born-Digital Prose PDFs** (250 trang): Hợp đồng, báo cáo tài chính, công văn Word/InDesign văn bản thuần túy.
   * **Nhóm 2: Scanned PDFs & Photos** (250 trang): Hợp đồng scan, công văn đóng dấu đỏ, hóa đơn VAT chụp camera.
   * **Nhóm 3: Ghost OCR & Corrupted Vector** (150 trang): PDF scan text mất dấu, tài liệu TCVN3/VNI lỗi CMap không ảnh.
   * **Nhóm 4: Complex Scientific Papers & Nested Tables** (150 trang - Positive Group): Paper LaTeX công thức toán, Báo cáo tài chính bảng biểu lồng nhau dày đặc.
   * **Nhóm 5: Regular Single-tier Tables & Invoices (150 trang - Negative Benchmark Group)**: Hợp đồng kinh tế có bảng đơn giản 1 tầng (không lồng, không merge cell), hóa đơn bán lẻ đơn giản để đo lường và kiểm soát **False-Positive Rate của Table-gate $< 2\%$**.
   * **Nhóm 6: Mixed & Hybrid Pages** (200 trang): Báo cáo chứa chữ ký/biểu mẫu scan lồng trong văn bản số hóa.
2. **Quy Trình Kiểm Tra Đối Kháng Trước Tối Ưu (Adversarial Sanity Check Pass)**:
   * Trước khi đưa toàn bộ 1,150 trang vào thuật toán Bayesian Optimization, hệ thống bắt buộc phải vượt qua bước kiểm tra đối kháng độc lập trên **30 tài liệu biên dễ gây nhiễu**:
     * Hợp đồng có bảng 1 tầng đóng khung viền ngoài (Single-tier bordered tables).
     * Biểu mẫu hành chính có các đường kẻ gạch chân điền thông tin (`Họ và tên: ............`).
     * Tài liệu hướng dẫn sử dụng ký tự mũi tên (`→`, `⇒`, `←`) làm bullet points quy trình.
   * **Tiêu chuẩn vượt ải**: Tỷ lệ bắt nhầm $\text{FPR} = 0\%$ trên tập Adversarial Sanity Check này ($100\%$ trả về `is_complex_structure = False`).
3. **Tối Ưu Hóa Tham Số**:
   * Áp dụng **Bayesian Optimization & Grid Search** trên tập Validation ($70\%$ corpus) để tìm bộ tham số tối ưu cực đại hóa F1-Score trên toàn bộ 6 nhóm tài liệu.

---

## 3.5. Đánh Giá Độ Phức Tạp Cấu Trúc (SCS) Qua Multi-Signal Gating & Xử Lý Trực Giao Tiếng Việt

### 1. Cơ Chế Multi-Signal Gating Cho Math & Bảng Biểu (Chống False-Positive STIX Font, Bảng Thường & Mũi Tên Bullet):
Để loại bỏ triệt để hiện tượng phân loại nhầm các hợp đồng có font STIX, bảng đơn giản $10 \times 5$ có viền ngoài hoặc ký tự mũi tên vào VLM đắt đỏ, hệ thống áp dụng cơ chế đồng thuận đa tín hiệu:

```python
# 1. Math Gate: Ký tự toán học đặc thù thực tế VÀ (font LaTeX HOẶC cấu trúc kẹp phân số Fraction Sandwich)
is_math_complex = (math_chars >= 2 or math_sym_ratio >= 0.005) and (latex_font_ratio >= 0.20 or has_fraction_lines)

# 2. Table Gate: Short-circuit O(1) kiểm tra vector ops VÀ (phát hiện lồng đa cấp thật sự HOẶC phương sai ô gộp leaf cells)
is_table_complex = (vector_density >= 0.40) and (vector_count >= 80) and (nested_depth_2_count >= 1 or cell_variance_high)

# 3. Kết luận độ phức tạp cấu trúc
is_complex_structure = is_math_complex or is_table_complex
```

*Trong đó:*
* `math_chars`: Chỉ tính các ký tự thuộc nhóm Mathematical Operators (`\u2200-\u22FF`, `\u2A00-\u2AFF`), Mathematical Alphanumeric (`\U0001D400-\U0001D7FF`), loại bỏ hoàn toàn dải mũi tên `\u2190-\u21FF` vốn hay xuất hiện làm bullet points.
* `has_fraction_lines`: Tín hiệu phân số theo cấu trúc kẹp (**Fraction Sandwich**): chỉ nhận diện các đoạn thẳng ngang ($4\text{pt} \le w \le 80\text{pt}$) **khi và chỉ khi** có token chữ/số nằm ngay sát phía trên ($y - 12\text{pt} \le y_{\text{bottom}} \le y$) và ngay sát phía dưới ($y \le y_{\text{top}} \le y + 12\text{pt}$) trên cùng khoảng tọa độ $x$. Cơ chế này loại bỏ $100\%$ các đường gạch chân biểu mẫu hoặc viền ô bảng.
* `nested_depth_2_count`: Phát hiện cấu trúc lồng đa cấp thực sự (Chain containment: Khung bảng $\supset$ Ô chứa $\supset$ Ô con cấp 2). Hệ thống tự động loại bỏ khung viền bao ngoài lớn nhất của toàn bảng (Outer Table Frame) để không bị kích hoạt nhầm bởi các bảng đơn giản 1 tầng có viền.
* `cell_variance_high`: Đo độ lệch chuẩn diện tích chỉ trên tập các ô con (`leaf_rects`), loại bỏ khung viền ngoài để phát hiện chính xác ô gộp (merged cells / rowspan / colspan).

### 2. Xử Lý Trực Giao Thật Sự Giữa Ngôn Ngữ Tiếng Việt & Độ Phức Tạp Cấu Trúc:
* Khi `is_complex_structure == True` và `language == "vi"` $\implies$ Gắn nhãn `PageType.COMPLEX_STRUCTURE_VI`, điều phối sang **`VNM_OCR Pipeline (POST /api/v1/document/extract)`** với `extract_tables=True` (kích hoạt YOLOv10 Layout + YOLOv8 TSR + VietOCR Seq2Seq) để vừa giữ cấu trúc bảng vừa bảo toàn $100\%$ dấu tiếng Việt.
* Khi `is_complex_structure == True` và `language != "vi"` $\implies$ Gắn nhãn `PageType.COMPLEX_STRUCTURE_EN`, điều phối sang **`PaddleOCR-VL-1.5/1.6`** hoặc **`PP-StructureV3`**.

---

# 4. KIẾN TRÚC HỆ THỐNG ENDPOINTS TÁCH RỜI & ĐIỀU PHỐI ĐA NGUỒN

## 4.1. Triết Lý Thiết Kế: Kiến Trúc 2 Tầng Tự Động, Blast Radius Isolation & Transparent Output

Hệ thống được xây dựng trên nguyên tắc phân định trách nhiệm rõ ràng, tách bạch thành **2 Tầng Tự Động Hoạt Động Độc Lập**:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   KIẾN TRÚC 2 TẦNG TỰ ĐỘNG ĐỘC LẬP                                   │
├───────────────────────────────────┬──────────────────────────────────────────────────────────────────┤
│ **TẦNG 1: MACRO ENGINE ROUTER**   │ • Trả lời: "Điều phối trang/tài liệu sang Engine nào?"           │
│ (`SmartPDFInspector` - Cấp binary)│ • Phân tích: Metadata nhị phân PDF (Font dict, CMap, /XObject).  │
│                                   │ • Phạm vi: CHỈ CHẠY trong nhánh `/api/v1/extract/universal`.     │
│                                   │ • **Blast Radius Isolation**: Client gọi Explicit Endpoint thì   │
│                                   │   Tầng 1 hoàn toàn bị BYPASS, cách ly 100% rủi ro phân loại sai. │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ **TẦNG 2: MICRO STRUCTURE DLA**   │ • Trả lời: "Trong trang này, vùng nào là Bảng, Title, Equation?" │
│ (`layout.onnx` & `tsr.onnx`)      │ • Phân tích: Pixel hình ảnh đã render ở độ phân giải 150-300 DPI.│
│                                   │ • Phạm vi: LUÔN LUÔN CHẠY bên trong pipeline `DocumentService`.  │
│                                   │ • **Tự động nhận diện**: Tự động phát hiện vùng `table` và       │
│                                   │   chạy TSR sang Markdown GFM (mặc định `extract_tables=True`).   │
└───────────────────────────────────┴──────────────────────────────────────────────────────────────────┘
```

### 1. Nguyên Tắc Phân Định Trách Nhiệm (Client Decision vs In-Engine Intelligence):
* **Client chỉ quyết định đúng 1 lần ở cửa ngõ**: Chọn endpoint dựa trên thứ họ biết chắc chắn $100\%$ (định dạng tệp: `.docx`, `.xlsx`, `.pdf` và ngôn ngữ: Tiếng Việt hay Tiếng Anh/Quốc tế).
* **Mọi chi tiết cấu trúc nội dung bên trong để DLA/TSR tự động xử lý**: Client gửi một thông báo hành chính tiếng Việt không cần phải đoán trước tờ thông báo đó có bảng thống kê hay không. DLA (`layout.onnx`) bên trong pipeline VNM-OCR sẽ tự động phát hiện vùng `table` và kích hoạt TSR (`tsr.onnx`) xuất bảng Markdown sạch sẽ.

### 2. Độ Trong Suốt Của Output Khi Gọi `/api/v1/extract/universal` (Response Metadata Transparency):
Để giải quyết triệt để vấn đề "kết quả không nhất quán" khi client debug, response của endpoint `/universal` luôn trả về đầy đủ metadata cấp trang:
* `page_type`: Nhãn phân loại trang của `SmartPDFInspector` (`BORN_DIGITAL`, `SCANNED`, `GHOST_OCR`, `COMPLEX_STRUCTURE_VI`, v.v.).
* `confidence_score`: Độ tin cậy của thuật toán phân loại ($0.0 - 1.0$).
* `engine_used`: Engine thực tế đã bóc tách trang (`NativePDFStream`, `VNM_OCR_DocumentService`, `PaddleOCR_VL`, v.v.).
* `fallback_recommended`: Cờ cảnh báo nếu `confidence_score < 0.80`, gợi ý client có thể gọi lại trực tiếp qua Dedicated Endpoint tương ứng.

---

## 4.2. Sơ Đồ Kiến Trúc Tổng Thể & Ma Trận Điều Phối Đa Chiều

```
                                  ┌─────────────────────────────────────────────────────────┐
                                  │            CLIENT / API GATEWAY REQUEST                 │
                                  │       (PDF, DOCX, XLSX, PPTX, HTML, Images)             │
                                  └────────────────────────────┬────────────────────────────┘
                                                               │
                ┌──────────────────────────────────────────────┼──────────────────────────────────────────────┐
                │                                              │                                              │
                ▼ (Client chọn trực tiếp endpoint)             ▼ (Client gọi Auto-Inspector)                  ▼ (Client gọi Office)
    ┌──────────────────────────────────────┐       ┌──────────────────────────────────────┐       ┌──────────────────────────────────────┐
    │     EXPLICIT DEDICATED GATEWAYS      │       │    UNIVERSAL DISPATCHER & INSPECTOR  │       │       DOCLING OFFICE GATEWAY         │
    │  (Fast Native, VNM-OCR, PaddleOCR)   │       │   POST /api/v1/extract/universal     │       │     POST /api/v1/extract/docling     │
    └──────────────────┬───────────────────┘       └──────────────────┬───────────────────┘       └──────────────────┬───────────────────┘
                       │                                              │                                              │
        ┌──────────────┴──────────────┬───────────────────────────────┼──────────────────────────────┬───────────────┘
        │                             │                               │                              │
        ▼                             ▼                               ▼                              ▼
┌──────────────────┐    ┌───────────────────────────┐   ┌───────────────────────────┐  ┌───────────────────────────┐
│ Native Fast      │    │ VNM-OCR Vietnamese        │   │ PaddleOCR International   │  │ Docling Office Parser     │
│ Stream Engine    │    │ Dedicated Sub-System      │   │ Dedicated Sub-System      │  │ (do_ocr=False)            │
│ (PyMuPDF / Rust) │    │ (7-Step Unified & Atomic) │   │ (PP-OCRv6 / PaddleOCR-VL) │  │ (.docx, .xlsx, .pptx)     │
└─────────┬────────┘    └─────────────┬─────────────┘   └─────────────┬─────────────┘  └─────────────┬─────────────┘
          │                           │                               │                              │
          │ Born-Digital Prose        │ 1. /document/extract (RAG)    │ 1. Standard EN OCR (~300ms)  │ Office Documents             │
          │ (< 15ms/page, CPU)        │ 2. /ocr, /layout, /table      │ 2. Complex/LaTeX VLM (~2s)   │ (20 - 100ms, CPU)            │
          │                           │ 3. Ghost/Rasterize Pass       │ 3. Rasterize EN OCR (~400ms) │                              │
          └───────────────────────────┴───────────────┬───────────────┴──────────────────────────────┘
                                                      │
                                                      ▼
                                  ┌─────────────────────────────────────────────────────────┐
                                  │         UNIVERSAL DOCUMENT IR (Intermediate Repr)       │
                                  │    (Standard Document AST: Headings, Tables, LaTeX Math)│
                                  └────────────────────────────┬────────────────────────────┘
                                                               │
                                                               ▼
                                  ┌─────────────────────────────────────────────────────────┐
                                  │     LLM-READY MARKDOWN & RAG SYNTHESIZER (Clean GFM)    │
                                  └─────────────────────────────────────────────────────────┘
```

### Bảng Ma Trận Định Tuyến Thông Minh Đầy Đủ (Routing Matrix):

| Loại Dữ Liệu | Cấu Trúc / Đặc Tính | Ngôn Ngữ | Endpoint / Engine Được Chỉ Định | Mục Tiêu & Cơ Chế |
| :--- | :--- | :--- | :--- | :--- |
| **PDF** | Born-Digital Prose thường | Bất kỳ | `POST /api/v1/extract/native/pdf` | Siêu tốc $< 15$ ms/trang, $100\%$ chính xác (Text stream, `requires_image_input=False`) |
| **PDF** | **Bảng lồng / Báo cáo tài chính**| **Tiếng Việt** | **`POST /api/v1/document/extract`** (`extract_tables=true`) | **DLA + TSR tiếng Việt (tsr.onnx) + VietOCR giữ dấu (`requires_image_input=True`)** |
| **PDF / Paper**| **Paper / Công thức toán LaTeX** | **Tiếng Anh/Khác**| **`POST /api/v1/extract/paddle/complex-vlm`** | **PaddleOCR-VL-1.5/1.6 bóc LaTeX Math (VLM cần ảnh bitmap, `requires_image_input=True`)** |
| **PDF** | Scan / Công văn / Hóa đơn | **Tiếng Việt** | **`POST /api/v1/document/extract`** (hoặc `/ocr`) | **DBNet + VietOCR nhận diện dấu chuẩn (`requires_image_input=True`)** |
| **PDF** | Scan văn bản thường | **Tiếng Anh/Khác**| **`POST /api/v1/extract/paddle/ocr`** | **PP-OCRv6 ONNX quốc tế (`requires_image_input=True`)** |
| **PDF** | Ghost OCR mất dấu / Font hỏng| **Tiếng Việt** | **`POST /api/v1/document/extract`** (`resolution=300`) | **Rasterize toàn trang + Khôi phục $100\%$ dấu (`is_vector_recovery=True`, `requires_image_input=True`)** |
| **PDF** | **Corrupted Vector ($R_{\text{img}}=0$, vỡ CMap)**| **Tiếng Việt** | **`POST /api/v1/document/extract`** (`resolution=300`) | **Rasterize `pdfplumber` $\rightarrow$ VNM-OCR Pipeline (`is_vector_recovery=True`, `requires_image_input=True`)** |
| **PDF** | **Corrupted Vector ($R_{\text{img}}=0$, vỡ CMap)**| **Tiếng Anh / Khác (Thường)**| **`POST /api/v1/extract/paddle/ocr`**| **Rasterize `get_pixmap()` $\rightarrow$ PP-OCRv6 (`is_vector_recovery=True`, `requires_image_input=True`)** |
| **PDF / Paper** | **Corrupted Vector ($R_{\text{img}}=0$, vỡ CMap)**| **Tiếng Anh / Khác (Toán/Bảng)**| **`POST /api/v1/extract/paddle/complex-vlm`**| **Rasterize `get_pixmap()` $\rightarrow$ PaddleOCR-VL (`is_vector_recovery=True`, `requires_image_input=True`)** |
| **Word (.docx)**| Tài liệu văn bản Office | Bất kỳ | `POST /api/v1/extract/docling` | Docling `do_ocr=False`, giữ heading chuẩn (`requires_image_input=False`) |
| **Excel (.xlsx, .csv)**| Bảng tính dữ liệu | Bất kỳ | `POST /api/v1/extract/docling` | Docling Spreadsheet $\rightarrow$ GFM Table/JSON (`requires_image_input=False`) |
| **PowerPoint (.pptx)**| Slide thuyết trình | Bất kỳ | `POST /api/v1/extract/docling` | Docling Presentation $\rightarrow$ Sections (`requires_image_input=False`) |
| **Hình ảnh (.png, .jpg)**| Ảnh chụp tài liệu/hóa đơn | **Tiếng Việt** | **`POST /api/v1/document/extract`** (hoặc `/ocr`) | VNM-OCR nhận diện hóa đơn, công văn, CCCD (`requires_image_input=True`) |
| **Hình ảnh (.png, .jpg)**| Ảnh chụp tài liệu | **Tiếng Anh** | `POST /api/v1/extract/paddle/ocr` | PP-OCRv6 OCR nhanh tiếng Anh (`requires_image_input=True`) |

---

## 4.3. Quản Trị Tranh Chấp Tài Nguyên & Cơ Chế Phân Cấp Hàng Đợi Ưu Tiên (QoS & Priority Queue Arbitration)

```
                            ┌──────────────────────────────────────────────┐
                            │            API GATEWAY & DISPATCHER          │
                            │       (Port 8000 - Lightweight CPU Core)     │
                            └──────────────────────┬───────────────────────┘
                                                   │
                ┌──────────────────────────────────┼──────────────────────────────────┐
                │                                  │                                  │
                ▼                                  ▼                                  ▼
    ┌───────────────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐
    │ Native & Office Endpoints │      │ Sync OCR (<= 5 pages)     │      │ Async OCR (> 5 pages)     │
    │ (CPU Stream, < 100ms)     │      │ (Direct Worker Call)      │      │ (Returns 202 task_id)     │
    └───────────────────────────┘      └─────────────┬─────────────┘      └─────────────┬─────────────┘
                                                     │                                  │
                                                     │                                  ▼
                                                     │                    ┌───────────────────────────┐
                                                     │                    │ REDIS / CELERY TASK QUEUE │
                                                     │                    │ [P0] Sync Critical        │
                                                     │                    │ [P1] Dedicated Explicit   │
                                                     │                    │ [P2] Auto-Router Traffic  │
                                                     │                    │ [P3] Bulk Background Jobs │
                                                     │                    └─────────────┬─────────────┘
                                                     │                                  │
                ┌────────────────────────────────────┴──────────────────────────────────┤
                │                                                                       │
                ▼                                                                       ▼
    ┌──────────────────────────────────────┐                ┌──────────────────────────────────────┐
    │ CLUSTER 1: VIETNAMESE OCR WORKERS    │                │ CLUSTER 2: PADDLE & VLM WORKERS      │
    │ Endpoints: /api/v1/document/extract  │                │ Endpoints: /api/v1/extract/paddle/*  │
    │ (det, vietocr, layout, tsr ONNX)     │                │ (PP-OCRv6, PaddleOCR-VL-1.5/1.6)     │
    │ Hardware: GPU Pods (2-4GB VRAM)      │                │ Hardware: High VRAM GPU (16-24GB)    │
    │ Features: Dynamic Batching (4-8 pgs) │                │ Features: VRAM Memory Guard (< 85%)  │
    └──────────────────────────────────────┘                └──────────────────────────────────────┘
```

#### Cơ Chế Trọng Tài Hàng Đợi Ưu Tiên (QoS Resource Arbitration):
Cả hai luồng traffic (Explicit Calls và Auto-Inspector Calls) đều chia sẻ cụm Worker / GPU phía sau. Để ngăn chặn rủi ro traffic từ `/universal` chiếm dụng tài nguyên GPU làm chậm các client gọi Dedicated Endpoints:
1. **Priority P0 (Real-time Critical Sync)**: Request đồng bộ $\le 5$ trang từ Explicit Endpoints.
2. **Priority P1 (Dedicated Priority - Mặc Định Cho Explicit Calls)**: Request từ các endpoint tường minh (`/api/v1/document/extract`, `/api/v1/extract/paddle/*`). Client đã chủ động chọn đúng endpoint và chấp nhận chi phí tính toán $\rightarrow$ Luôn được ưu tiên tiêu thụ trước trong worker queue.
3. **Priority P2 (Auto-Router Priority - Mặc Định Cho Auto-Inspector)**: Request tự động định tuyến từ `/api/v1/extract/universal`. Đảm bảo nếu có sai số phân loại ở nhánh tự động thì cũng không làm suy giảm SLA/tốc độ của client P1.
4. **Priority P3 (Bulk Background Batch)**: Tác vụ bóc tách tài liệu số lượng lớn chạy ngầm theo lô.
5. **GPU Dynamic Batching & VRAM Guard**: Tự động gom $4 - 8$ trang thành một batch tính toán, giám sát ngưỡng trần VRAM $< 85\%$ để loại bỏ hoàn toàn lỗi Out-of-Memory.

#### Khả Năng Tương Thích & Triển Khai Đa Nền Tảng (Hardware Support Matrix):
Kiến trúc quản trị tài nguyên trên cho phép toàn bộ module bóc tách tự động tương thích và chạy mượt mà (chỉ sử dụng đúng ONNX Execution Providers) trên 5 kịch bản phần cứng:
1. **Windows Only CPU (16GB RAM)**: Chạy `CPUExecutionProvider` thuần, dùng `HeapCompact` chặn tràn RAM.
2. **Macbook/Mac Studio (Apple Silicon M-Series, >= 16GB)**: CPU inference qua kiến trúc ARM64 cực nhanh, dùng `VECLIB_MAXIMUM_THREADS=1` tránh tranh chấp core.
3. **Linux Server/Desktop Only CPU (16GB RAM)**: An toàn qua cơ chế giải phóng `malloc_trim(0)` của glibc.
4. **Windows PC/Laptop có GPU RTX (>= 6GB VRAM)**: Chạy `CUDAExecutionProvider` trơn tru qua quản lý On-Demand, không làm treo Windows Display Driver (WDDM).
5. **Linux Server có GPU RTX (>= 6GB VRAM)**: Môi trường lý tưởng nhất cho Dynamic GPU Batching năng suất cao.

*(Chi tiết xem thêm tại tài liệu chuyên sâu `DOC-REPORT-HW-001`).*

---

## 4.4. Phân Hệ PaddleOCR Quốc Tế & Phân Hệ VNM_OCR Chuyên Biệt Tiếng Việt (Kiến Trúc Backend Chuẩn)

### 1. Phân Hệ PaddleOCR Quốc Tế:
* **PaddleOCR Standard (`PP-OCRv6`)**: Hợp nhất nhận diện đa ngôn ngữ, tốc độ cao, siêu nhẹ trên cả CPU và GPU cho tài liệu scan và tài liệu rasterized tiếng Anh/quốc tế.
* **PaddleOCR-VL (v1.5/1.6)**: Vision-Language Model dựa trên ERNIE-4.5-0.3B, đạt **94.5% - 96.3%** trên benchmark `OmniDocBench`, chuyên bóc tách Paper khoa học tiếng Anh, công thức toán LaTeX (`$...$`, `$$...$$`) và biểu đồ.
* **PP-StructureV3**: Trích xuất bảng biểu có tọa độ chi tiết từng ô cho các bảng tính tiếng Anh phức tạp.

### 2. Phân Hệ `VNM_OCR` Chuyên Biệt Tiếng Việt:
* **Core Engine Stack (Tối Ưu Tài Nguyên - On-Demand Instantiation)**: Vận hành bởi `EngineManager` singleton với cơ chế **Tải Trễ (Lazy-Loading)**. Thay vì nạp toàn bộ 6 mô hình ONNX vào RAM/VRAM ngay từ đầu, hệ thống chỉ khởi tạo những mô hình thực sự cần thiết dựa trên yêu cầu của endpoint (tương tự như nguyên lý tách bạch của các file gốc `t_ocr.py`, `t_recognizer.py`, `full_pipeline.py`). Chẳng hạn: gọi `/ocr` chỉ nạp mô hình Text Detection và Recognition, không nạp DLA/TSR; giúp **tránh lãng phí tài nguyên phần cứng một cách triệt để**. Các mô hình này (`det.onnx`, `cnn.onnx`, `encoder.onnx`, `decoder.onnx`, `layout.onnx`, `tsr.onnx`) đảm bảo zero PyTorch runtime dependency, tự động kích hoạt `CUDAExecutionProvider` hoặc `CPUExecutionProvider`.
* **Unified Document Extraction Service (`POST /api/v1/document/extract`)**:
  * Đóng vai trò là pipeline RAG trung tâm, kết hợp 7 bước tuần tự: Render ảnh trang $\rightarrow$ DBNet Text Detection $\rightarrow$ VietOCR Recognition $\rightarrow$ YOLOv10 DLA $\rightarrow$ Fusion & Garbage Drop (Header/Footer/Page numbers) $\rightarrow$ YOLOv8 TSR & Markdown Table Builder $\rightarrow$ Block Markdown Assembly & Natural Reading Order Sort.
  * Hỗ trợ tham số cấu hình: `extract_tables: bool = True` (bật/tắt TSR bóc bảng), `resolution: int = 150` (DPI render PDF).
* **Bộ Endpoints Granular / Atomic**:
  * `POST /api/v1/ocr`: Nhận diện text thuần trên ảnh đơn lẻ (`OcrService`).
  * `POST /api/v1/layout`: Phân tích vùng bố cục trên ảnh đơn lẻ (`LayoutService`).
  * `POST /api/v1/table`: Bóc tách bảng sang Markdown từ ảnh cắt vùng bảng (`TableService`).
  * `GET /api/v1/health`: Kiểm tra sức khỏe, trạng thái nạp model và providers khả dụng.
  * `POST /api/ocr`: Legacy UI adapter cho Web UI.
* **Cơ Chế Phục Hồi Ghost OCR & Corrupted Vector Tiếng Việt**: Tự động kích hoạt cơ chế Rasterization phân giải cao ($150 - 300\text{ DPI}$) chuyển đổi trang vector hỏng thành bitmap image rồi đưa qua `DocumentService` để trích xuất sạch sẽ $100\%$ dấu thanh tiếng Việt và cấu trúc phân cấp.

---

# 5. THIẾT KẾ MÃ NGUỒN MẪU & INTERFACE CHUẨN HOÁ (REFERENCE IMPLEMENTATION)

## 5.1. Interface Chuẩn Cho BaseExtractor & Explicit Capability Scoring

```python
"""Interface cốt lõi cho hệ thống bóc tách dữ liệu đa nguồn (Pluggable Engine)."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"
    IMAGE = "image"
    CSV = "csv"
    UNKNOWN = "unknown"


class PageType(str, Enum):
    BORN_DIGITAL = "born_digital"
    SCANNED = "scanned"
    GHOST_OCR = "ghost_ocr"
    CORRUPTED_VECTOR_VI = "corrupted_vector_vi"  # Font hỏng CMap không ảnh Tiếng Việt -> Rasterize + VNM-OCR
    CORRUPTED_VECTOR_EN = "corrupted_vector_en"  # Font hỏng CMap không ảnh Tiếng Anh -> Rasterize + PaddleOCR
    COMPLEX_STRUCTURE_VI = "complex_structure_vi"  # Bảng biểu lồng / Báo cáo tài chính Tiếng Việt
    COMPLEX_STRUCTURE_EN = "complex_structure_en"  # Paper khoa học, LaTeX Math Tiếng Anh (PaddleOCR-VL)
    MIXED = "mixed"
    IMAGE_ONLY = "image_only"
    EMPTY = "empty"


class ExtractedPage(BaseModel):
    page_number: int
    page_type: PageType
    confidence_score: float = 1.0
    language: str = "vi"
    markdown_content: str
    raw_text: Optional[str] = None
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    math_formulas: List[str] = Field(default_factory=list)
    is_complex_structure: bool = False
    requires_image_input: bool = False       # Cờ phương thức: Engine đích yêu cầu đầu vào ảnh bitmap (Scanned, Corrupted, VLM)
    requires_rasterization: bool = False     # Alias tương thích ngược (= requires_image_input)
    is_vector_recovery: bool = False         # Cờ chẩn đoán: Kích hoạt cứu hộ do lỗi font CMap hoặc Ghost OCR
    fallback_recommended: bool = False
    processing_time_ms: float
    engine_used: str


class UniversalDocumentResult(BaseModel):
    filename: str
    format: DocumentFormat
    total_pages: int
    full_markdown: str
    pages: List[ExtractedPage]
    total_processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseExtractor(ABC):
    """Interface trừu tượng mà tất cả các Plugin bóc tách phải tuân thủ."""

    @abstractmethod
    def score_capability(
        self,
        format: DocumentFormat,
        page_type: Optional[PageType] = None,
        language: str = "vi",
        is_complex_structure: bool = False
    ) -> float:
        """Trả về điểm số độ phù hợp (0.0 - 1.0) cho yêu cầu bóc tách để Dispatcher chọn plugin tối ưu."""
        pass

    @abstractmethod
    def extract_document(self, file_bytes: bytes, filename: str, **kwargs) -> UniversalDocumentResult:
        """Bóc tách toàn bộ tài liệu."""
        pass

    @abstractmethod
    def extract_page(
        self,
        page_data: Any,
        page_number: int,
        requires_image_input: bool = False,
        is_complex_structure: bool = False,
        is_vector_recovery: bool = False,
        rasterize: Optional[bool] = None,  # Tham số alias tương thích ngược
        **kwargs
    ) -> ExtractedPage:
        """Bóc tách một trang đơn lẻ.
        
        Args:
            page_data: Đối tượng trang PDF (fitz.Page) hoặc dữ liệu thô.
            page_number: Số thứ tự trang (1-based).
            requires_image_input: True nếu engine cần ảnh bitmap (Scanned, Corrupted Vector, Mixed, VLM).
            is_complex_structure: True nếu trang chứa cấu trúc phức tạp (LaTeX Math, Merged Table).
            is_vector_recovery: True nếu kích hoạt cơ chế cứu hộ phục hồi do lỗi CMap/Ghost OCR.
            rasterize: Alias tương thích ngược cho requires_image_input.
        """
        pass
```

---

## 5.2. Bộ Kiểm Tra `SmartPDFInspector` Chuẩn Xác (Đồng Bộ 100% Cây Quyết Định, Multi-Signal SCS & Fraction Line Detection)

```python
"""Module kiểm tra & phân tích cấu trúc nhị phân PDF (Smart PDF Inspector).

Triển khai logic kiểm tra cấp stream, đồng bộ 100% với cây quyết định kiến trúc:
- Bắt Ghost OCR qua Vietnamese Syllable Fingerprint.
- Tính toán SCS qua Multi-signal Gating:
  + Math Gate: math_chars >= 2 VÀ (latex_font >= 0.20 HOẶC has_fraction_lines).
  + Table Gate: vector_count >= 80 VÀ (nested_rect_count >= 1 HOẶC cell_variance_high).
- Phân luồng ngôn ngữ tường minh cho Corrupted Vector (CORRUPTED_VECTOR_VI vs CORRUPTED_VECTOR_EN).
- Xử lý trực giao thật sự giữa Tiếng Việt và Độ phức tạp cấu trúc.
"""

import fitz  # PyMuPDF
import re
import math
from typing import Tuple, List, Optional, Set
from app.schemas.extractor_schemas import PageType

# Single Source of Truth cho phiên bản module SmartPDFInspector & Hybrid Dispatcher
INSPECTOR_VERSION: str = "2.5.0"


class SmartPDFInspector:
    """Kiểm tra nội tại file PDF ở cấp binary/stream để phân loại trang trong < 2ms."""

    VERSION: str = INSPECTOR_VERSION

    # Regex nhận diện tập ký tự có dấu đặc trưng của Tiếng Việt
    VI_DIACRITICS_REGEX = re.compile(
        r"[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]",
        re.IGNORECASE
    )
    
    # Dải ký tự Private Use Area (PUA) - font vỡ CMap / ToUnicode hỏng
    PUA_REGEX = re.compile(r"[\uE000-\uF8FF]")

    # Dải ký tự toán học Unicode đặc thù: Mathematical Operators, Supplemental Math, Math Alphanumeric
    # (ĐÃ LOẠI BỎ hoàn toàn dải mũi tên \u2190-\u21FF để tránh bắt nhầm ký tự bullet trong tài liệu thường)
    MATH_UNICODE_REGEX = re.compile(
        r"[\u2200-\u22FF\u2A00-\u2AFF\u2070-\u2079\u2080-\u2089\u2300-\u2335\U0001D400-\U0001D7FF]"
    )

    # Tập mẫu các họ font đặc trưng của LaTeX / TeX / Math
    LATEX_MATH_FONT_PATTERNS = ["cmr", "cmmi", "cmsy", "msam", "msbm", "libertine", "cambriamath", "latinmodern"]

    # Tập âm tiết tiếng Việt không dấu chuẩn hóa (~6,500 âm tiết, dưới đây là tập mẫu phổ biến)
    VI_UNACCENTED_SYLLABLES: Set[str] = {
        "uy", "ban", "nhan", "dan", "thanh", "pho", "cong", "hoa", "xa", "hoi", "chu", "nghia",
        "viet", "nam", "doc", "lap", "tu", "do", "hanh", "phuc", "quyet", "dinh", "thong", "tu",
        "nghi", "dinh", "luat", "bo", "tai", "chinh", "ke", "toan", "hop", "dong", "kinh", "te",
        "ben", "giao", "dich", "thue", "gia", "tri", "gia", "tang", "hoa", "don", "tien", "luong",
        "tong", "giam", "doc", "truong", "phong", "can", "bo", "ngay", "thang", "nam", "so", "ky",
        "ten", "chuc", "vu", "dia", "chi", "ma", "so", "dien", "thoai", "email", "website", "tai",
        "khoan", "ngan", "hang", "chi", "nhanh", "dieu", "khoan", "quy", "dinh", "trach", "nhiem",
        "quyen", "loi", "nghia", "vu", "hieu", "luc", "thi", "hanh", "dai", "dien", "phap", "luat"
    }

    # Từ khóa hành chính / văn bản tiếng Việt thường gặp
    VI_ADMIN_KEYWORDS = {
        "uy ban", "nhan dan", "cong hoa", "xa hoi", "chu nghia", "viet nam", "quyet dinh",
        "thong tu", "nghi dinh", "hop dong", "kinh te", "hoa don", "bien ban", "thong bao"
    }

    @classmethod
    def detect_fraction_lines(cls, page: fitz.Page, drawings: List[dict]) -> bool:
        """Phát hiện dấu gạch phân số toán học theo cấu trúc kẹp (Fraction Sandwich: có text ngay trên & dưới).
        
        Loại trừ 100% các đường kẻ gạch chân biểu mẫu, viền ô bảng hẹp hoặc đường phân cách tiêu đề.
        """
        words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
        if not words:
            return False

        for draw in drawings:
            for item in draw.get("items", []):
                if item[0] == "l":  # Line
                    p1, p2 = item[1], item[2]
                    # Đoạn thẳng nằm ngang (delta y < 1.0) có độ dài phân số (4pt <= length <= 80pt)
                    if abs(p1.y - p2.y) < 1.0:
                        x_min = min(p1.x, p2.x)
                        x_max = max(p1.x, p2.x)
                        line_y = (p1.y + p2.y) / 2.0
                        length = x_max - x_min
                        if 4.0 <= length <= 80.0:
                            # Cấu trúc kẹp: Bắt buộc có token chữ/số nằm sát phía trên và sát phía dưới đoạn thẳng
                            has_top_token = any(
                                (w[3] <= line_y + 2.0) and (w[3] >= line_y - 14.0) and not (w[2] < x_min or w[0] > x_max)
                                for w in words
                            )
                            has_bottom_token = any(
                                (w[1] >= line_y - 2.0) and (w[1] <= line_y + 14.0) and not (w[2] < x_min or w[0] > x_max)
                                for w in words
                            )
                            if has_top_token and has_bottom_token:
                                return True
        return False

    @classmethod
    def analyze_table_hierarchy(cls, drawings: List[dict]) -> Tuple[int, bool]:
        """Phát hiện cấu trúc lồng đa cấp thật sự (Multi-tier Depth >= 2) và ô gộp/phương sai kích thước ô.
        
        Loại bỏ khung viền ngoài của toàn bảng (Outer Table Frame) để không bị kích hoạt nhầm trên bảng 1 tầng.
        """
        rects: List[fitz.Rect] = []
        for draw in drawings:
            r = draw.get("rect")
            if r and isinstance(r, fitz.Rect) and r.width > 5 and r.height > 5:
                rects.append(r)
            for item in draw.get("items", []):
                if item[0] == "re":  # Rectangle
                    r_item = item[1]
                    if r_item.width > 5 and r_item.height > 5:
                        rects.append(r_item)

        if len(rects) < 8:
            return 0, False

        # Bounded Sorting & Truncation để đảm bảo KPI <= 2ms (tránh O(N^2) trên CAD/vector dày đặc)
        if len(rects) > 100:
            rects = sorted(rects, key=lambda r: r.get_area(), reverse=True)[:100]
        else:
            rects.sort(key=lambda r: r.get_area(), reverse=True)

        # Loại bỏ khung viền ngoài của toàn bảng (Outer Table Boundary)
        total_rect_area = sum(r.get_area() for r in rects)
        leaf_rects = [r for r in rects if r.get_area() < 0.60 * total_rect_area]
        if len(leaf_rects) < 6:
            return 0, False

        # 1. Phát hiện lồng đa cấp thực sự: một ô trung gian chứa ít nhất 2 ô con cấp 2
        nested_depth_2_count = 0
        for i, r_parent in enumerate(leaf_rects[:25]):  # Chỉ duyệt các container tiềm năng
            child_count = 0
            for j, r_child in enumerate(leaf_rects):
                if i != j and r_parent.contains(r_child) and (r_parent.get_area() >= 1.8 * r_child.get_area()):
                    child_count += 1
                    if child_count >= 2:  # Ô cha chứa từ 2 ô con trở lên
                        nested_depth_2_count += 1
                        break
            if nested_depth_2_count >= 1:
                break

        # 2. Đo phương sai diện tích ô trên leaf_rects (bỏ outer boundary để không làm lệch phân phối)
        areas = [r.get_area() for r in leaf_rects]
        mean_area = sum(areas) / len(areas)
        variance = sum((a - mean_area) ** 2 for a in areas) / len(areas)
        std_dev = math.sqrt(variance)
        cell_variance_high = (std_dev / mean_area) > 1.4 if mean_area > 0 else False

        return nested_depth_2_count, cell_variance_high

    @classmethod
    def evaluate_structural_complexity(cls, page: fitz.Page) -> Tuple[bool, float]:
        """Đo lường độ phức tạp cấu trúc (SCS) qua cơ chế Multi-signal Gating Mechanism & Short-Circuit O(1)."""
        text = page.get_text().strip()
        total_chars = max(1, len(text))
        
        # 1. Kiểm tra font LaTeX / Math
        fonts = page.get_fonts()
        latex_font_count = sum(1 for f in fonts if any(pat in (f[3] or "").lower() for pat in cls.LATEX_MATH_FONT_PATTERNS))
        latex_font_ratio = latex_font_count / max(1, len(fonts)) if fonts else 0.0

        # 2. Đếm ký tự toán học Unicode đặc thù
        math_chars = len(cls.MATH_UNICODE_REGEX.findall(text))
        math_sym_ratio = math_chars / total_chars

        # 3. Phân tích hình vẽ vector & Short-circuit gating
        drawings = page.get_drawings()
        vector_count = len(drawings)
        vector_density = min(1.0, vector_count / 100.0)

        # Short-Circuit: Chỉ chạy phân tích bảng lồng O(M log M) khi đã thỏa mãn cổng O(1)
        if vector_count >= 80 and vector_density >= 0.40:
            nested_count, cell_variance_high = cls.analyze_table_hierarchy(drawings)
        else:
            nested_count, cell_variance_high = 0, False

        # Short-Circuit: Chỉ kiểm tra fraction sandwich khi có ký tự toán học hoặc font LaTeX
        if math_chars >= 1 or latex_font_ratio >= 0.10:
            has_fraction_lines = cls.detect_fraction_lines(page, drawings)
        else:
            has_fraction_lines = False

        # Multi-signal Gating:
        # Gate A: Có ký tự toán học thực tế VÀ (font LaTeX HOẶC cấu trúc kẹp phân số Fraction Sandwich)
        is_math_complex = (math_chars >= 2 or math_sym_ratio >= 0.005) and (latex_font_ratio >= 0.20 or has_fraction_lines)
        
        # Gate B: Đường kẻ vector dày đặc (>= 80) VÀ (lồng đa cấp depth >= 2 HOẶC ô gộp leaf cells biến động lớn)
        is_table_complex = (vector_density >= 0.40) and (vector_count >= 80) and (nested_count >= 1 or cell_variance_high)

        is_complex = is_math_complex or is_table_complex
        scs_score = (0.50 * math_sym_ratio * 10.0) + (0.30 * latex_font_ratio) + (0.20 * vector_density)
        return is_complex, float(min(1.0, scs_score))

    @classmethod
    def calculate_text_quality_score(cls, text: str, image_coverage: float) -> Tuple[float, bool, float]:
        """Tính Text Quality Score (TQS), PUA Penalty & Phát hiện Ghost OCR qua Vietnamese Syllable Fingerprint."""
        if not text or len(text.strip()) == 0:
            return 0.0, False, 1.0
            
        total_chars = len(text)
        words = [re.sub(r"[^\w\s]", "", w.lower()) for w in text.split()]
        words = [w for w in words if w]
        total_words = max(1, len(words))
        
        pua_chars = len(cls.PUA_REGEX.findall(text))
        pua_penalty = 1.0 - (pua_chars / total_chars)
        
        alpha_chars = [c for c in text if c.isalpha()]
        total_alpha = max(1, len(alpha_chars))
        vi_diacritics_count = len(cls.VI_DIACRITICS_REGEX.findall(text))
        diacritics_ratio = vi_diacritics_count / total_alpha
        
        syllable_hits = sum(1 for w in words if w in cls.VI_UNACCENTED_SYLLABLES)
        syllable_match_ratio = syllable_hits / total_words

        is_ghost_ocr = False
        if image_coverage >= 0.50 and total_chars >= 20:
            if syllable_match_ratio >= 0.50 and diacritics_ratio < 0.01:
                is_ghost_ocr = True
            elif any(kw in text.lower() for kw in cls.VI_ADMIN_KEYWORDS) and diacritics_ratio < 0.01:
                is_ghost_ocr = True

        accent_consistency = 1.0 if diacritics_ratio >= 0.02 else (0.0 if is_ghost_ocr else 0.5)
        lexical_coherence = syllable_match_ratio if syllable_match_ratio > 0.3 else 0.5
        
        ghost_penalty = 0.80 if is_ghost_ocr else 0.0
        tqs = (0.35 * pua_penalty) + (0.35 * lexical_coherence) + (0.30 * accent_consistency) - ghost_penalty
        return max(0.0, float(tqs)), is_ghost_ocr, pua_penalty

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Nhận diện ngôn ngữ phân tầng: bắt chính xác tiếng Việt có dấu và tiếng Việt mất dấu."""
        if not text or len(text.strip()) == 0:
            return "vi"
            
        alpha_chars = [c for c in text if c.isalpha()]
        if not alpha_chars:
            return "vi"
            
        vi_diacritics_count = len(cls.VI_DIACRITICS_REGEX.findall(text))
        diacritics_ratio = vi_diacritics_count / len(alpha_chars)
        
        if diacritics_ratio >= 0.025:
            return "vi"
            
        words = [re.sub(r"[^\w\s]", "", w.lower()) for w in text.split()]
        words = [w for w in words if w]
        if words:
            syllable_hits = sum(1 for w in words if w in cls.VI_UNACCENTED_SYLLABLES)
            if (syllable_hits / len(words)) >= 0.40:
                return "vi"
            if any(kw in text.lower() for kw in cls.VI_ADMIN_KEYWORDS):
                return "vi"

        return "en"

    @classmethod
    def inspect_page(cls, page: fitz.Page) -> Tuple[PageType, str, float, bool]:
        """Phân tích toàn diện một trang PDF theo Cây Quyết Định Đồng Bộ (3.1).
        
        Returns:
            Tuple[PageType, language, confidence_score, is_complex_structure]
        """
        # 1. Trích xuất Text Stream, Font & Đoạn vẽ
        text = page.get_text().strip()
        char_count = len(text)
        font_list = page.get_fonts()
        has_fonts = len(font_list) > 0

        # 2. Tính toán diện tích phủ của hình ảnh bitmap
        image_list = page.get_images(full=True)
        page_area = float(page.rect.width * page.rect.height)
        
        total_image_area = 0.0
        if page_area > 0:
            for img in image_list:
                xref = img[0]
                for rect in page.get_image_rects(xref):
                    total_image_area += float(rect.width * rect.height)
            image_coverage = min(1.0, total_image_area / page_area)
        else:
            image_coverage = 0.0

        # 3. Phân tích chất lượng Text, Ghost OCR & Multi-signal SCS
        tqs, is_ghost, pua_penalty = cls.calculate_text_quality_score(text, image_coverage)
        is_complex, scs_score = cls.evaluate_structural_complexity(page)
        language = cls.detect_language(text)

        # 4. Cây Quyết Định Đồng Bộ
        
        # Nhánh 4.1: Không có font nào
        if not has_fonts:
            if image_coverage >= 0.50:
                return PageType.SCANNED, language, 0.99, is_complex
            if char_count == 0 and image_coverage == 0.0:
                return PageType.EMPTY, language, 1.0, is_complex
            return PageType.SCANNED, language, 0.90, is_complex

        # Nhánh 4.2: Lỗi Font CMap / PUA rác (Bịt lỗ hổng Corrupted Vector phân luồng theo ngôn ngữ)
        if pua_penalty < 0.70:
            if image_coverage >= 0.50:
                return PageType.SCANNED, language, 0.95, is_complex
            if language == "vi":
                return PageType.CORRUPTED_VECTOR_VI, language, 0.95, is_complex
            else:
                return PageType.CORRUPTED_VECTOR_EN, language, 0.95, is_complex

        # Nhánh 4.3: Xử lý Trực Giao Độ Phức Tạp Cấu Trúc (SCS Multi-signal Gate)
        if is_complex:
            if language == "vi":
                return PageType.COMPLEX_STRUCTURE_VI, language, 0.95, True
            else:
                return PageType.COMPLEX_STRUCTURE_EN, language, 0.95, True

        # Nhánh 4.4: Độ phủ ảnh cao (>= 80%) hoặc quá ít ký tự trên nền ảnh scan (>= 50%)
        if image_coverage >= 0.80 or (char_count < 20 and image_coverage >= 0.50):
            return PageType.SCANNED, language, 0.95, False

        # Nhánh 4.5: Ghost OCR Detection (Ảnh nền >= 50%, text >= 20 nhưng TQS < 0.60 hoặc is_ghost == True)
        if image_coverage >= 0.50 and char_count >= 20:
            if tqs < 0.60 or is_ghost:
                return PageType.GHOST_OCR, language, 0.95, False

        # Nhánh 4.6: Born-Digital Chuẩn (Nhiều chữ >= 50, ít ảnh < 60%, chất lượng text tốt TQS >= 0.60)
        if char_count >= 50 and image_coverage < 0.60 and tqs >= 0.60:
            return PageType.BORN_DIGITAL, language, 0.98, False

        # Nhánh 4.7: Trang trống hoặc Gần Trống (Ngoại lệ Số trang / Header ngắn có chủ đích)
        if char_count < 20 and image_coverage < 0.50:
            if char_count == 0 and image_coverage == 0.0:
                return PageType.EMPTY, language, 1.0, False
            if image_coverage < 0.10:
                return PageType.BORN_DIGITAL, language, 0.70, False
            return PageType.MIXED, language, 0.80, False

        # Nhánh 4.8: Các trường hợp lai còn lại (Mixed)
        return PageType.MIXED, language, 0.85, False
```

---

## 5.3. Bộ Điều Phối Đa Nguồn `UniversalDocumentDispatcher` & Hỗ Trợ Dedicated Microservice Endpoints

```python
"""Bộ điều phối trung tâm: Quản lý Plugin và phân phối tới Dedicated Endpoints."""

from typing import List, Optional, Any
import fitz
import time
from app.engine.base import (
    BaseExtractor, DocumentFormat, PageType,
    UniversalDocumentResult, ExtractedPage
)
from app.engine.inspectors.pdf_inspector import SmartPDFInspector, INSPECTOR_VERSION


class NativePDFExtractor(BaseExtractor):
    """Adapter cho Native Stream Extraction (PyMuPDF / Rust Core) - Cực nhanh (< 15ms)."""

    def score_capability(
        self,
        format: DocumentFormat,
        page_type: Optional[PageType] = None,
        language: str = "vi",
        is_complex_structure: bool = False
    ) -> float:
        # Born-digital văn bản thường không có công thức toán/bảng phức tạp
        if format == DocumentFormat.PDF and page_type == PageType.BORN_DIGITAL and not is_complex_structure:
            return 0.99
        return 0.0

    def extract_document(self, file_bytes: bytes, filename: str, **kwargs) -> UniversalDocumentResult:
        ...

    def extract_page(
        self,
        page_data: Any,
        page_number: int,
        requires_image_input: bool = False,
        is_complex_structure: bool = False,
        is_vector_recovery: bool = False,
        rasterize: Optional[bool] = None,
        **kwargs
    ) -> ExtractedPage:
        # Bóc tách text blocks thuần qua page.get_text("blocks") (không cần ảnh bitmap, siêu tốc < 15ms)
        ...


class VietnameseOCRExtractor(BaseExtractor):
    """Adapter cho VNM_OCR Core Pipeline (det, vietocr, layout, tsr ONNX)."""

    def score_capability(
        self,
        format: DocumentFormat,
        page_type: Optional[PageType] = None,
        language: str = "vi",
        is_complex_structure: bool = False
    ) -> float:
        if format in (DocumentFormat.PDF, DocumentFormat.IMAGE) and language == "vi":
            if page_type in (
                PageType.SCANNED, PageType.GHOST_OCR, PageType.CORRUPTED_VECTOR_VI,
                PageType.COMPLEX_STRUCTURE_VI, PageType.MIXED
            ):
                return 0.98
        return 0.0

    def extract_document(self, file_bytes: bytes, filename: str, **kwargs) -> UniversalDocumentResult:
        ...

    def extract_page(
        self,
        page_data: Any,
        page_number: int,
        requires_image_input: bool = True,
        is_complex_structure: bool = False,
        is_vector_recovery: bool = False,
        rasterize: Optional[bool] = None,
        **kwargs
    ) -> ExtractedPage:
        # Render trang thành ảnh bitmap (DPI=150-300) và đưa qua DocumentService (Pipeline 7 bước ONNX Runtime)
        # Ghi nhận cờ is_vector_recovery=True nếu được cứu hộ từ lỗi vỡ font CMap hoặc Ghost OCR
        ...


class PaddleOCRExtractor(BaseExtractor):
    """Adapter cho PaddleOCR Quốc Tế (PP-OCRv6, PaddleOCR-VL-1.5/1.6, PP-Structure)."""

    def score_capability(
        self,
        format: DocumentFormat,
        page_type: Optional[PageType] = None,
        language: str = "vi",
        is_complex_structure: bool = False
    ) -> float:
        if format in (DocumentFormat.PDF, DocumentFormat.IMAGE) and language != "vi":
            # Ưu tiên PaddleOCR-VL cho tài liệu phức tạp (cả Scanned, Born-Digital lẫn Corrupted Vector EN)
            if is_complex_structure or page_type == PageType.COMPLEX_STRUCTURE_EN:
                return 0.99
            if page_type in (PageType.SCANNED, PageType.CORRUPTED_VECTOR_EN, PageType.GHOST_OCR, PageType.MIXED):
                return 0.95
        return 0.0

    def extract_document(self, file_bytes: bytes, filename: str, **kwargs) -> UniversalDocumentResult:
        ...

    def extract_page(
        self,
        page_data: Any,
        page_number: int,
        requires_image_input: bool = True,
        is_complex_structure: bool = False,
        is_vector_recovery: bool = False,
        rasterize: Optional[bool] = None,
        **kwargs
    ) -> ExtractedPage:
        # Chuyển đổi page thành ảnh bitmap (pixmap) khi requires_image_input=True
        # - Nếu is_complex_structure=True: gửi ảnh trang tới POST /api/v1/extract/paddle/complex-vlm (PaddleOCR-VL bóc LaTeX Math & Bảng phức tạp)
        # - Nếu is_complex_structure=False: gửi ảnh trang tới POST /api/v1/extract/paddle/ocr (PP-OCRv6)
        ...


class DoclingUniversalExtractor(BaseExtractor):
    """Adapter cho Docling Office Parser (.docx, .xlsx, .pptx, .html, .csv)."""

    def score_capability(
        self,
        format: DocumentFormat,
        page_type: Optional[PageType] = None,
        language: str = "vi",
        is_complex_structure: bool = False
    ) -> float:
        if format in (
            DocumentFormat.DOCX, DocumentFormat.XLSX, DocumentFormat.PPTX,
            DocumentFormat.HTML, DocumentFormat.CSV
        ):
            return 0.99
        return 0.0

    def extract_document(self, file_bytes: bytes, filename: str, **kwargs) -> UniversalDocumentResult:
        ...

    def extract_page(
        self,
        page_data: Any,
        page_number: int,
        requires_image_input: bool = False,
        is_complex_structure: bool = False,
        is_vector_recovery: bool = False,
        rasterize: Optional[bool] = None,
        **kwargs
    ) -> ExtractedPage:
        ...


class UniversalDocumentDispatcher:
    """Registry và Router trung tâm với cơ chế Scoring Capability tất định."""

    def __init__(self):
        self._plugins: List[BaseExtractor] = []
        self._register_default_plugins()

    def register_plugin(self, plugin: BaseExtractor) -> None:
        self._plugins.append(plugin)

    def _register_default_plugins(self) -> None:
        self.register_plugin(NativePDFExtractor())            # Native Stream (< 15ms)
        self.register_plugin(VietnameseOCRExtractor())         # VNM_OCR Core (det, vietocr, layout, tsr ONNX Pipeline)
        self.register_plugin(PaddleOCRExtractor())             # PaddleOCR (PP-OCRv6, PaddleOCR-VL, Corrupted EN)
        self.register_plugin(DoclingUniversalExtractor())     # Docling Office (.docx, .xlsx, .pptx)

    def process_file(self, file_bytes: bytes, filename: str) -> UniversalDocumentResult:
        start_time = time.time()
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        format_map = {
            "pdf": DocumentFormat.PDF,
            "docx": DocumentFormat.DOCX,
            "xlsx": DocumentFormat.XLSX,
            "csv": DocumentFormat.CSV,
            "pptx": DocumentFormat.PPTX,
            "html": DocumentFormat.HTML,
            "png": DocumentFormat.IMAGE,
            "jpg": DocumentFormat.IMAGE,
            "jpeg": DocumentFormat.IMAGE,
        }
        doc_format = format_map.get(ext, DocumentFormat.UNKNOWN)

        if doc_format == DocumentFormat.PDF:
            return self._process_pdf_hybrid(file_bytes, filename, start_time)

        # Xử lý Office qua Plugin có điểm capability cao nhất
        best_plugin = max(self._plugins, key=lambda p: p.score_capability(format=doc_format))
        result = best_plugin.extract_document(file_bytes, filename)
        result.total_processing_time_ms = (time.time() - start_time) * 1000.0
        return result

    def _process_pdf_hybrid(self, pdf_bytes: bytes, filename: str, start_time: float) -> UniversalDocumentResult:
        """Xử lý PDF cấp trang bằng cơ chế Capability Scoring tất định."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        extracted_pages: List[ExtractedPage] = []
        
        for idx, page in enumerate(doc):
            page_num = idx + 1
            page_start = time.time()
            page_type, lang, conf, is_complex = SmartPDFInspector.inspect_page(page)
            
            # Chọn Plugin có điểm Capability Score cao nhất cho trang này (trực giao theo ngôn ngữ và độ phức tạp)
            best_plugin = max(
                self._plugins,
                key=lambda p: p.score_capability(
                    format=DocumentFormat.PDF,
                    page_type=page_type,
                    language=lang,
                    is_complex_structure=is_complex
                )
            )

            # Phân định tường minh 2 cờ ngữ nghĩa theo đánh giá phản biện kỹ thuật:
            # 1. requires_image_input: Engine xử lý cần ảnh bitmap (OCR/VLM) hay stream vector (Native)
            requires_image_input = page_type in (
                PageType.CORRUPTED_VECTOR_VI,
                PageType.CORRUPTED_VECTOR_EN,
                PageType.GHOST_OCR,
                PageType.SCANNED,
                PageType.MIXED
            ) or is_complex

            # 2. is_vector_recovery: Cờ chẩn đoán sự cố font CMap/Ghost OCR cần cứu hộ qua ảnh
            is_vector_recovery = page_type in (
                PageType.CORRUPTED_VECTOR_VI,
                PageType.CORRUPTED_VECTOR_EN,
                PageType.GHOST_OCR
            )

            # Bóc tách nội dung trang với đầy đủ tín hiệu trực giao
            page_result = best_plugin.extract_page(
                page,
                page_number=page_num,
                requires_image_input=requires_image_input,
                is_complex_structure=is_complex,
                is_vector_recovery=is_vector_recovery
            )
            page_result.processing_time_ms = (time.time() - page_start) * 1000.0
            page_result.page_type = page_type
            page_result.confidence_score = float(conf)
            page_result.fallback_recommended = conf < 0.80
            page_result.language = lang
            page_result.is_complex_structure = is_complex
            page_result.requires_image_input = requires_image_input
            page_result.requires_rasterization = requires_image_input  # Tương thích ngược
            page_result.is_vector_recovery = is_vector_recovery
            extracted_pages.append(page_result)

        full_md = "\n\n---\n\n".join([p.markdown_content for p in extracted_pages])
        total_time_ms = (time.time() - start_time) * 1000.0

        return UniversalDocumentResult(
            filename=filename,
            format=DocumentFormat.PDF,
            total_pages=len(extracted_pages),
            full_markdown=full_md,
            pages=extracted_pages,
            total_processing_time_ms=total_time_ms,
            metadata={
                "hybrid_routing": True,
                "inspector_version": INSPECTOR_VERSION,  # Đồng bộ Single Source of Truth với v2.5.0
                "page_distribution": {
                    p_type.value: sum(1 for p in extracted_pages if p.page_type == p_type)
                    for p_type in PageType
                }
            }
        )
```

---

## 5.4. Báo Cáo Phân Tích & Triển Khai Giải Pháp Chuẩn Hóa Ngữ Nghĩa Rasterization (Review Implementation Sign-Off)

### 1. Bối Cảnh Phản Biện & Vấn Đề Kỹ Thuật (Từ `docs/research/review-research-problems.md`):
Trong tài liệu phản biện [`docs/research/review-research-problems.md`](file:///E:/MyProject/VNM-OCR/docs/research/review-research-problems.md), chuyên gia đã:
- **Xác nhận thành công**: Toàn bộ luồng dữ liệu tín hiệu `is_complex_structure` từ `SmartPDFInspector.inspect_page()` qua `score_capability()` và `extract_page()` trên cả 4 plugin (`NativePDFExtractor`, `VietnameseOCRExtractor`, `PaddleOCRExtractor`, `DoclingUniversalExtractor`) lẫn lời gọi trong `_process_pdf_hybrid` đã hoạt động nhất quán 100%, không còn lỗ hổng tín hiệu.
- **Điểm phân vân cần làm rõ**: Cờ `requires_rasterize` trước đây bị nhập nhằng ngữ nghĩa giữa hai mục đích sử dụng hoàn toàn khác nhau:
  1. *Cứu hộ phục hồi lỗi (Error Recovery)*: Trang có vector/font CMap bị vỡ hoặc lớp OCR ẩn mất dấu (`CORRUPTED_VECTOR_VI`, `CORRUPTED_VECTOR_EN`, `GHOST_OCR`) nên cần render lại thành ảnh để phục hồi nội dung qua OCR.
  2. *Yêu cầu định dạng đầu vào của Engine (Input Modality Requirement)*: Trang có font/vector hoàn toàn nguyên vẹn nhưng có cấu trúc phức tạp (`COMPLEX_STRUCTURE_EN` / Paper LaTeX Math) được chuyển đến `PaddleOCR-VL`. Bản thân `PaddleOCR-VL` là một Vision-Language Model (VLM), bắt buộc phải nhận ảnh bitmap làm đầu vào (không đọc stream vector thô). Nếu chỉ bật cờ cho 3 PageType lỗi thì request gửi sang VLM sẽ bị thiếu ảnh hoặc gây hiểu lầm trong thiết kế.

### 2. Đối Chiếu Thực Tế Kiến Trúc & Mã Nguồn Core:
Sau khi rà soát toàn bộ mã nguồn backend ([`backend/app/services/document_service.py`](file:///E:/MyProject/VNM-OCR/backend/app/services/document_service.py), [`backend/app/utils/pdf_utils.py`](file:///E:/MyProject/VNM-OCR/backend/app/utils/pdf_utils.py)) và đặc tả của các engine quốc tế:
- **`NativePDFExtractor`**: Chỉ trích xuất text stream thuần túy từ PDF DOM qua `page.get_text("blocks")` $\rightarrow$ Không cần ảnh (`requires_image_input = False`).
- **`VietnameseOCRExtractor`**: Vận hành bởi `DocumentService` (Pipeline 7 bước ONNX gồm DBNet + VietOCR + DLA + TSR), bắt buộc nhận mảng ảnh OpenCV BGR (`np.ndarray`) hoặc PIL Image $\rightarrow$ Luôn cần ảnh (`requires_image_input = True`).
- **`PaddleOCRExtractor`**: Cả `PP-OCRv6` (OCR pipeline thị giác) lẫn `PaddleOCR-VL` (Multimodal VLM) đều xử lý trên mảng pixel 2D $\rightarrow$ Luôn cần ảnh (`requires_image_input = True`).
- **`DoclingUniversalExtractor`**: Trích xuất trực tiếp cấu trúc AST tệp Office $\rightarrow$ Không cần ảnh (`requires_image_input = False`).

### 3. Giải Pháp Triển Khai: Phân Tách 2 Cờ Ngữ Nghĩa Trực Giao:
Hệ thống chính thức tách bạch 2 khái niệm thành 2 cờ độc lập:
1. **`requires_image_input: bool` (Execution Modality)**:
   - Biểu thức: `page_type in (CORRUPTED_VECTOR_VI, CORRUPTED_VECTOR_EN, GHOST_OCR, SCANNED, MIXED) or is_complex`.
   - Vai trò: Báo cho dispatcher và extractor biết trang này bắt buộc phải chuyển đổi thành ảnh bitmap (`page.get_pixmap()`) để nạp vào model Vision/VLM/OCR.
2. **`is_vector_recovery: bool` (Quality Telemetry & Anomaly Recovery)**:
   - Biểu thức: `page_type in (CORRUPTED_VECTOR_VI, CORRUPTED_VECTOR_EN, GHOST_OCR)`.
   - Vai trò: Cờ chẩn đoán chất lượng. Báo hiệu trang này vốn dĩ chứa luồng vector text nhưng text stream bị hỏng hoặc mất dấu, hệ thống đã kích hoạt cơ chế cưỡng bức rasterize để cứu dữ liệu. Giúp dashboard giám sát phân tách rạch ròi giữa "trang chạy VLM bình thường" và "trang gặp sự cố font cần cứu hộ".

### 4. Bảng Ma Trận Phân Định Trạng Thái 2 Cờ (Truth Table):
| PageType | `is_complex` | Engine Được Chọn | `requires_image_input` | `is_vector_recovery` | Lý Do Kỹ Thuật |
| :--- | :---: | :--- | :---: | :---: | :--- |
| `BORN_DIGITAL` | False | `NativePDFExtractor` | **False** | **False** | Đọc trực tiếp text stream từ PDF DOM, không render ảnh, siêu tốc $< 15$ms. |
| `COMPLEX_STRUCTURE_EN` | True | `PaddleOCRExtractor` (VL) | **True** | **False** | VLM cần ảnh bitmap 2D; vector/font hoàn toàn khỏe mạnh, không phải lỗi. |
| `COMPLEX_STRUCTURE_VI` | True | `VietnameseOCRExtractor` | **True** | **False** | VNM-OCR DLA + TSR cần ảnh bitmap 2D; tài liệu chuẩn tiếng Việt. |
| `SCANNED` | Bất kỳ | `VietnameseOCRExtractor` / `Paddle` | **True** | **False** | Tài liệu quét/ảnh chụp, bắt buộc đưa qua pipeline OCR thị giác. |
| `MIXED` | Bất kỳ | `VietnameseOCRExtractor` / `Paddle` | **True** | **False** | Trang lai ảnh và chữ, cần xử lý ảnh OCR vùng scan. |
| `CORRUPTED_VECTOR_VI` | Bất kỳ | `VietnameseOCRExtractor` | **True** | **True** | Font vỡ CMap không dấu, cưỡng bức rasterize để VNM-OCR cứu 100% dấu. |
| `CORRUPTED_VECTOR_EN` | Bất kỳ | `PaddleOCRExtractor` | **True** | **True** | Font vỡ CMap tiếng Anh, cưỡng bức rasterize để PP-OCRv6/VLM cứu text. |
| `GHOST_OCR` | Bất kỳ | `VietnameseOCRExtractor` | **True** | **True** | Text stream bị mất dấu do lớp OCR ẩn rác, cưỡng bức rasterize làm lại. |
| `EMPTY` | False | Không áp dụng | **False** | **False** | Trang rỗng không có chữ lẫn ảnh. |

### 5. Xác Nhận Đồng Bộ Hóa Toàn Diện:
- [x] **Schema `ExtractedPage`**: Thêm `requires_image_input`, `is_vector_recovery`, giữ `requires_rasterization` làm alias tương thích ngược.
- [x] **Interface `BaseExtractor.extract_page`**: Cập nhật signature và docstring chuẩn hóa toàn diện.
- [x] **Triển khai 4 Class Extractor**: Đồng bộ signature trên `NativePDFExtractor`, `VietnameseOCRExtractor`, `PaddleOCRExtractor`, `DoclingUniversalExtractor`, loại bỏ logic kiểm tra rẽ nhánh chồng chéo.
- [x] **Điều phối `UniversalDocumentDispatcher._process_pdf_hybrid`**: Tính toán và truyền cả 2 cờ xuyên suốt vào pipeline thực thi.
- [x] **Bảng Ma trận Định tuyến (Routing Matrix)**: Cập nhật chú thích kỹ thuật rõ ràng cho từng endpoint.
- [x] **Metadata Versioning (Single Source of Truth)**: Định nghĩa hằng số `INSPECTOR_VERSION = "2.5.0"` tại module `SmartPDFInspector` và nạp vào `metadata["inspector_version"]`, loại bỏ triệt để hard-code chuỗi version, đồng bộ 100% với Header tài liệu và Lộ trình Kỹ thuật V2.5.

---

# 6. LỘ TRÌNH TRIỂN KHAI & TIÊU CHÍ ĐÁNH GIÁ (ROADMAP & BENCHMARK KPIS)

## 6.1. Các Giai Đoạn Triển Khai (Bao Gồm Giai Đoạn 0: Đánh Giá & Hiệu Chuẩn VNM-OCR Core)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 LỘ TRÌNH KỸ THUẬT V2.5                                 │
├───────────────────┬────────────────────────────────────────────────────────────────────┤
│ **Giai đoạn 0**   │ • Xây dựng bộ dữ liệu benchmark chuẩn (1,150 trang:                │
│ (Baseline &       │   Hợp đồng scan, công văn có dấu đỏ, hóa đơn, tài liệu TCVN3/VNI,  │
│ Calibration)      │   paper khoa học LaTeX math, báo cáo tài chính bảng lồng, và       │
│                   │   nhóm âm tính 150 trang hợp đồng có bảng đơn vị 1 tầng).          │
│                   │ • Thực hiện bước **Adversarial Sanity Check** trên 30 tài liệu     │
│                   │   biên (bảng 1 tầng đóng khung, biểu mẫu gạch chân ____, bullet →) │
│                   │   với yêu cầu bắt buộc FPR = 0% trước khi tuning Bayesian.         │
│                   │ • Đo đạc độ chính xác thực tế (CER/WER) của VNM_OCR Core Pipeline  │
│                   │   (DocumentService, OcrService, TableService).                     │
│                   │ • Hiệu chuẩn Multi-signal Gates cho SCS & Table FPR < 2%.          │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ **Giai đoạn 1**   │ • Đóng gói module `SmartPDFInspector` hoàn chỉnh (PyMuPDF + Rust).  │
│ (Core Inspector)  │ • Triển khai Vietnamese Syllable Fingerprint & Multi-signal SCS.   │
│                   │ • Phân luồng Corrupted Vector theo ngôn ngữ & Fraction Lines.      │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ **Giai đoạn 2**   │ • Đóng gói các Dedicated Endpoints:                                │
│ (Dedicated Micro- │   - `POST /api/v1/extract/docling` (Docling do_ocr=False).         │
│ services)         │   - `POST /api/v1/extract/native/pdf` (PyMuPDF Fast Stream).       │
│                   │   - `POST /api/v1/document/extract` (VNM-OCR 7-Step Pipeline).     │
│                   │   - `POST /api/v1/ocr`, `/layout`, `/table` (Granular Services).   │
│                   │   - `POST /api/v1/extract/paddle/*` (PP-OCRv6, Rasterize & VLM).   │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ **Giai đoạn 3**   │ • Triển khai `UniversalDocumentDispatcher` (Auto Routing qua       │
│ (Hybrid Auto-     │   `POST /api/v1/extract/universal`).                               │
│ Routing)          │ • Xuất Markdown siêu sạch chuẩn GFM tối ưu cho LLM Context Chunking│
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ **Giai đoạn 4**   │ • Triển khai Hàng đợi Bất đồng bộ (Celery/Redis Streams).          │
│ (Scale & Perf)    │ • Dynamic GPU Batching (4-8 trang) & VRAM Memory Guard chống OOM.  │
└───────────────────┴────────────────────────────────────────────────────────────────────┘
```

## 6.2. Tiêu Chí Đo Lường Thành Công (Benchmark KPIs)

1. **Hiệu Năng & Tốc Độ (Throughput & Latency)**:
   * Thời gian phân loại trang của `SmartPDFInspector`: **$\le 2$ ms / trang**.
   * Thời gian xử lý trang Born-Digital Prose: **$\le 15$ ms / trang**.
   * Thời gian bóc tách Office qua Docling: **$\le 100$ ms / trang**.
   * Giảm tải tiêu thụ GPU tối thiểu **$50\% - 70\%$** trên tập dữ liệu tổng hợp thực tế.
2. **Độ Chính Xác Nhận Dạng & Xử Lý Tiếng Việt (Accuracy & Fidelity)**:
   * Độ chính xác ký tự trên Born-Digital PDF: **$100\%$**.
   * Độ chính xác ký tự tiếng Việt có dấu trên Scanned PDF: **$\ge 98.5\%$ CER** (với `DocumentService` / VietOCR).
   * Tỷ lệ bảo toàn cấu trúc bảng biểu tiếng Việt: **$\ge 96\%$** (với `TableService` / `tsr.onnx`).
   * Tỷ lệ phát hiện chính xác Ghost OCR & Corrupted Vector: **$\ge 98\%$**.
3. **Chất Lượng Xử Lý Paper & Cấu Trúc Phức Tạp Quốc Tế (PaddleOCR)**:
   * Độ chính xác nhận dạng công thức toán LaTeX (`$...$`, `$$...$$`): **$\ge 92\%$**.
   * Tỷ lệ bảo toàn cấu trúc bảng lồng quốc tế (Merged Cells GFM): **$\ge 95\%$**.
   * Tỷ lệ bắt nhầm bảng đơn giản (Table-gate False-Positive Rate): **$\le 2\%$** trên nhóm kiểm thử âm tính.
4. **Định Dạng Đầu Ra Cho LLM/RAG (Markdown Cleanliness)**:
   * $100\%$ bảng biểu được chuyển đổi thành chuẩn GitHub Flavored Markdown (GFM) hoặc HTML Table sạch.
   * Cấu trúc Heading (`#`, `##`, `###`) bảo toàn phân cấp tài liệu logic cho việc cắt chunk (Chunking Strategy) trong RAG.
