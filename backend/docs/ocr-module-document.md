# Tài liệu Kỹ thuật & Hướng dẫn Tích hợp Mô-đun OCR & Document Extraction (FastAPI Backend)

Tài liệu này cung cấp thông tin chi tiết về mặt kiến trúc, các cải tiến hiệu năng, cấu trúc API, và hướng dẫn dành cho lập trình viên để tích hợp dịch vụ OCR & Document Extraction Tiếng Việt vào hệ thống số hóa tài liệu tổng thể và các pipeline RAG / Chatbot.

---

## 1. Tổng quan Cấu trúc Thư mục Backend Chuẩn Hóa

Cấu trúc phân cấp của thư mục `backend/` theo tiêu chuẩn Clean Architecture:

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                      # FastAPI Dependency Injection
│   │   └── v1/
│   │       ├── router.py                # Tổng hợp Router v1
│   │       └── endpoints/
│   │           ├── health.py            # GET /api/v1/health (Liveness & Providers)
│   │           ├── ocr.py               # POST /api/v1/ocr (Ảnh đơn)
│   │           ├── layout.py            # POST /api/v1/layout (YOLOv10 Layout)
│   │           ├── table.py             # POST /api/v1/table (TSR sang Markdown)
│   │           └── document.py          # POST /api/v1/document/extract (Full RAG Pipeline)
│   ├── core/
│   │   ├── config.py                    # Pydantic BaseSettings
│   │   ├── constants.py                 # Hằng số nhãn Layout, TSR, token IDs
│   │   └── logging.py                   # Rotating File & Console Logger
│   ├── engine/                          # [PORTABLE MODULE THUẦN ONNX]
│   │   ├── __init__.py                  # Public exports
│   │   ├── layout_engine.py             # YOLOv10 Document Layout Analysis (1024x1024)
│   │   ├── manager.py                   # EngineManager Singleton & Warmup
│   │   ├── model_loader.py              # Loader & Session Cache (Auto CPU/CUDA)
│   │   ├── ocr_engine.py                # TextDetector (DBNet) + TextRecognizer (VietOCR)
│   │   ├── operators.py                 # Pure NumPy/OpenCV image operators (Resize, Normalize, NMS)
│   │   ├── postprocess.py               # DBPostProcess (Shapely, Pyclipper)
│   │   ├── table_engine.py              # YOLOv8 Table Structure Recognition & Markdown builder
│   │   └── vocab.py                     # Standalone VietVocab Decoder (Offset +4, No PyTorch)
│   ├── exceptions/
│   │   ├── custom.py                    # AppException domain classes
│   │   └── handlers.py                  # Global FastAPI exception handlers
│   ├── schemas/                         # Pydantic V2 I/O Models
│   │   ├── common.py                    # Point2D, BaseResponse[T]
│   │   ├── ocr.py                       # OCRLineResult, OCRResponse
│   │   ├── layout.py                    # LayoutRegionResult, LayoutResponse
│   │   ├── table.py                     # TableComponent, TableMarkdownResponse
│   │   └── document.py                  # DocumentPageResult, DocumentExtractionResponse
│   ├── services/                        # Business Logic Layer
│   │   ├── ocr_service.py               # Single/batch OCR service & legacy adapter
│   │   ├── layout_service.py            # Layout analysis orchestration
│   │   ├── table_service.py             # TSR + OCR markdown construction
│   │   └── document_service.py          # 7-Step Sequence Document Extraction Pipeline
│   └── utils/
│       ├── image_utils.py               # Safe Unicode image byte decoding & PIL transforms
│       └── pdf_utils.py                 # PDF page rendering qua pdfplumber
├── models/                              # 6 file trọng số ONNX
│   ├── cnn.onnx
│   ├── decoder.onnx
│   ├── det.onnx
│   ├── encoder.onnx
│   ├── layout.onnx
│   └── tsr.onnx
├── tests/                               # 42 unit & integration test cases (Pytest)
├── Dockerfile                           # Multi-stage build (~1-1.5 GB)
├── docker-compose.yml
├── pyproject.toml                       # Dependencies tách [cpu], [gpu], [pdf], [dev]
└── README.md
```

---

## 2. Kiến trúc Hoạt động & Luồng Xử lý Dữ liệu

### 2.1 Luồng Xử lý Trích xuất Tài liệu Toàn diện cho RAG (`DocumentService`)

```
[Client gửi file PDF / Ảnh Scan]
              │
              ▼
    1. Render PDF Pages (pdfplumber) ──► List[OpenCV Image]
              │
              ▼ (Lặp qua từng trang)
    2. Full Page Text Detection & OCR ──► List[TextBoxes + Recognized Text]
              │
              ▼
    3. Document Layout Analysis (layout.onnx) ──► List[LayoutRegion: Title, Text, Table, Figure, Eq...]
              │
              ▼
    4. Layout & Text Fusion
       - Gán layout_type cho từng TextBox
       - Lọc bỏ vùng rác (Header/Footer lặp lại, số trang)
       - Sắp xếp thứ tự đọc tự nhiên (Top-to-bottom, Left-to-right)
              │
              ▼
    5. Xử lý Phân Nhánh Bảng Biểu vs Văn Bản Thường:
       ├─► [Vùng Table]:
       │     a. Crop ảnh vùng bảng
       │     b. Run TSR (tsr.onnx) ──► Cột, Dòng, Header, Spanning Cell
       │     c. Map tọa độ ô bảng + Text ──► Markdown Table (`| Cột 1 | Cột 2 |`)
       │
       └─► [Vùng Text / Title / Caption / Equation]:
             a. Ghép dòng chữ theo đoạn văn
             b. Định dạng Markdown: Title (`## ...`), Caption (`*...*`), Eq (`$$ ... $$`)
              │
              ▼
    6. Hợp nhất (Merge) Nội dung Trang theo Tọa độ Y ──► `page_markdown`
              │
              ▼
    7. Ghép nối Đa trang ──► `full_markdown` thống nhất cho RAG Text Splitters
```

---

## 3. Danh Sách REST Endpoints (API Reference)

### 3.1 `GET /api/v1/health`
- **Mô tả**: Kiểm tra trạng thái liveness, model readiness và execution providers.
- **Phản hồi**:
  ```json
  {
    "status": "ok",
    "models_ready": true,
    "available_providers": ["CPUExecutionProvider"]
  }
  ```

### 3.2 `POST /api/v1/document/extract` (Endpoint chính cho RAG/Chatbot)
- **Mô tả**: Nhận file PDF đa trang hoặc file ảnh scan, trích xuất toàn bộ sang chuỗi Markdown bảo toàn bố cục và bảng biểu.
- **Tham số**:
  - `file` (UploadFile): File PDF hoặc ảnh.
  - `extract_tables` (bool, default `true`): Có chạy TSR để bóc tách bảng hay không.
  - `resolution` (int, default `150`): DPI render PDF.
- **Phản hồi mẫu**:
  ```json
  {
    "total_pages": 1,
    "full_markdown": "## BÁO CÁO TÀI CHÍNH\n\n| TÀI SẢN | MÃ SỐ | SỐ CUỐI NĂM |\n| --- | --- | --- |\n| Tiền và tương đương tiền | 110 | 1.500.000.000 |\n\n*Ghi chú: Đơn vị tính VND*",
    "pages": [
      {
        "page_number": 1,
        "text_lines": [...],
        "layout_regions": [...],
        "tables_markdown": ["| TÀI SẢN | MÃ SỐ | SỐ CUỐI NĂM |\n| --- | --- | --- |\n| Tiền và tương đương tiền | 110 | 1.500.000.000 |"],
        "page_markdown": "..."
      }
    ],
    "elapsed_ms": 12450.5
  }
  ```

### 3.3 `POST /api/v1/ocr`
- **Mô tả**: Nhận diện chữ trên ảnh đơn lẻ.
- **Phản hồi**:
  ```json
  {
    "lines": [
      {
        "bbox": [[32, 15], [200, 15], [200, 40], [32, 40]],
        "text": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "score": 0.9982
      }
    ],
    "total_lines": 1,
    "elapsed_ms": 120.5
  }
  ```

### 3.4 `POST /api/v1/layout`
- **Mô tả**: Phân tích các khối bố cục tài liệu (Title, Text, Table, Figure, Caption, Equation).

### 3.5 `POST /api/v1/table`
- **Mô tả**: Nhận diện cấu trúc và chuyển đổi ảnh bảng biểu sang bảng Markdown.

### 3.6 `POST /api/ocr` (Legacy UI Adapter)
- **Mô tả**: Duy trì định dạng mảng lồng `[ [bbox, [text, score]] ]` tương thích 100% cho giao diện web `/ui`.

---

## 4. Hướng Dẫn Tích Hợp Vào Dự Án RAG / Chatbot

### Cách 1: Sử dụng như một Microservice độc lập qua REST API

```python
import httpx
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

def extract_pdf_for_rag(pdf_path: str) -> list[Document]:
    # 1. Gửi file PDF đến OCR Service
    with open(pdf_path, "rb") as f:
        response = httpx.post(
            "http://localhost:8000/api/v1/document/extract",
            files={"file": (pdf_path, f, "application/pdf")},
            params={"extract_tables": "true"},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

    # 2. Tạo Document từ full_markdown
    full_md = data["full_markdown"]
    raw_doc = Document(page_content=full_md, metadata={"source": pdf_path, "pages": data["total_pages"]})

    # 3. Tiến hành chunking theo Header Markdown để giữ nguyên ngữ cảnh bảng biểu và đoạn văn
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = markdown_splitter.split_text(raw_doc.page_content)
    return chunks
```

---

### Cách 2: Copy-Paste Module Trực Tiếp (In-Process Library)

1. **Copy các thư mục sau vào dự án mới**:
   - `backend/app/engine/` -> Đặt vào thư mục engine trong dự án mới.
   - `backend/models/*.onnx` -> Đặt vào thư mục `models/` trong dự án mới.
2. **Cài đặt thư viện tối giản**:
   ```bash
   # CPU:
   pip install onnxruntime opencv-python-headless numpy pillow pdfplumber shapely pyclipper
   # GPU:
   pip install onnxruntime-gpu opencv-python-headless numpy pillow pdfplumber shapely pyclipper
   ```
3. **Thực thi trực tiếp**:
   ```python
   from app.engine import EngineManager
   from app.services.document_service import DocumentService

   manager = EngineManager(models_dir="./models", device="auto")
   manager.initialize()

   doc_service = DocumentService(manager)
   with open("data/sample.pdf", "rb") as f:
       res = doc_service.extract_document(f.read())
   print(res.full_markdown)
   ```
