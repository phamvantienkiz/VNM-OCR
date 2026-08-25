# Vietnamese OCR & Document Extraction Backend Service

Dịch vụ backend FastAPI chuẩn hóa cho bài toán nhận dạng ký tự quang học (OCR) Tiếng Việt, phân tích bố cục tài liệu (DLA) và trích xuất bảng biểu sang Markdown (TSR) phục vụ quy trình nạp tài liệu cho các hệ thống RAG (Retrieval-Augmented Generation) và AI Agents / Chatbots.

---

## 1. Tính Năng Nổi Bật

- **Pure ONNX Runtime 100%**: Loại bỏ hoàn toàn sự phụ thuộc vào PyTorch trong quá trình suy luận production, giúp tăng tốc độ khởi động và giảm kích thước Docker image xuống còn **~1-1.5 GB**.
- **Bộ Giải Mã Từ Vựng Tiếng Việt Độc Lập**: Khớp chuẩn xác cơ chế token offset `+4` của VietOCR mà không cần nạp PyTorch model.
- **Pipeline Trích Xuất Tài Liệu Tự Động Cho RAG**:
  - Hỗ trợ tệp PDF đa trang và tệp ảnh scan (`.png`, `.jpg`, `.webp`, `.bmp`).
  - Nhận diện bố cục (Title, Text, Table, Figure, Caption, Equation).
  - Tự động lọc vùng rác (header, footer, số trang lặp lại).
  - Chuyển đổi bảng biểu phức tạp thành bảng Markdown chuẩn (`| Cột 1 | Cột 2 |`).
  - Trả về `full_markdown` bảo toàn thứ tự đọc tự nhiên của tài liệu.
- **Tương Thích Ngược Web UI**: Duy trì endpoint adapter `POST /api/ocr` tương thích 100% với giao diện visual demo cũ tại `/ui`.

---

## 2. Cài Đặt & Khởi Chạy

### 2.1 Cài đặt Môi trường Ảo

```bash
# Di chuyển vào thư mục backend
cd backend

# Tạo môi trường ảo Python
python -m venv .venv

# Kích hoạt môi trường ảo (Windows PowerShell):
.\.venv\Scripts\Activate.ps1
# (Linux/macOS):
# source .venv/bin/activate

# Nâng cấp pip
python -m pip install --upgrade pip
```

### 2.2 Cài đặt Dependencies

Lựa chọn nhóm dependencies phù hợp với môi trường triển khai của bạn:

```bash
# 1. Chạy trên CPU thuần túy (Khuyên dùng cho server không có GPU):
pip install -e ".[cpu,pdf]"

# 2. Chạy với GPU NVIDIA CUDA:
pip install -e ".[gpu,pdf]"

# 3. Môi trường phát triển & kiểm thử (Development):
pip install -e ".[cpu,pdf,dev]"
```

### 2.3 Khởi Chạy Backend Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Visual Web Demo**: [http://localhost:8000/ui](http://localhost:8000/ui)

---

## 3. Danh Sách REST Endpoints (API Reference)

| Endpoint | Method | Input Payload | Mô tả & Định dạng trả về |
| :--- | :---: | :--- | :--- |
| **`/api/v1/health`** | `GET` | Không | Kiểm tra trạng thái service, model readiness và danh sách ONNX Execution Providers khả dụng. |
| **`/api/v1/document/extract`** | `POST` | `multipart/form-data`<br>- `file`: PDF hoặc Ảnh<br>- `extract_tables`: boolean (default: `true`)<br>- `resolution`: int (DPI, default: `150`) | **Endpoint chính cho RAG/Chatbot**:<br>Trích xuất toàn bộ tài liệu đa trang thành chuỗi `full_markdown` thống nhất và dữ liệu chi tiết từng trang. |
| **`/api/v1/ocr`** | `POST` | `multipart/form-data`<br>- `file`: File ảnh | Nhận dạng chữ trên ảnh đơn lẻ, trả về danh sách `lines` kèm bounding box, text và score. |
| **`/api/v1/layout`** | `POST` | `multipart/form-data`<br>- `file`: File ảnh<br>- `threshold`: float (default: `0.5`) | Nhận dạng các khối bố cục tài liệu (Title, Text, Table, Figure, Caption, Equation). |
| **`/api/v1/table`** | `POST` | `multipart/form-data`<br>- `file`: Ảnh crop vùng bảng<br>- `threshold`: float (default: `0.2`) | Nhận dạng cấu trúc hàng/cột và chuyển đổi bảng biểu sang chuỗi bảng Markdown. |
| **`/api/ocr`** | `POST` | `multipart/form-data`<br>- `file`: File ảnh | Adapter endpoint cho Web UI demo cũ (`[ [bbox, [text, score]] ]`). |

---

## 4. Hướng Dẫn Tích Hợp Vào Dự Án RAG / Chatbot

### Lựa Chọn 1: Sử dụng như một Microservice độc lập qua REST API (Khuyên dùng)

#### Ví dụ gọi bằng Python (`httpx` / `requests`):
```python
import httpx

def extract_document_markdown(file_path: str) -> str:
    url = "http://localhost:8000/api/v1/document/extract"
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        response = httpx.post(url, files=files, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["full_markdown"]

# Sử dụng trong LangChain RAG pipeline:
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

markdown_content = extract_document_markdown("data/bao_cao_tai_chinh.pdf")
doc = Document(page_content=markdown_content, metadata={"source": "bao_cao_tai_chinh.pdf"})

# Tiến hành chunking theo Header Markdown:
headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
splits = splitter.split_text(doc.page_content)
```

---

### Lựa Chọn 2: Copy-Paste Module Trực Tiếp (In-Process Library)

Nếu bạn muốn nhúng trực tiếp module OCR vào source code của một dự án khác mà không dựng server riêng:

1. **Copy các thư mục sau vào dự án mới**:
   - Copy toàn bộ thư mục `backend/app/engine/` vào thư mục engine của dự án mới.
   - Copy 6 tệp weights ONNX trong `backend/models/` vào thư mục `models/` của dự án mới:
     - `det.onnx`
     - `cnn.onnx`
     - `encoder.onnx`
     - `decoder.onnx`
     - `layout.onnx`
     - `tsr.onnx`
2. **Cài đặt các dependencies tối giản**:
   ```bash
   # Dành cho CPU:
   pip install onnxruntime opencv-python-headless numpy pillow pdfplumber shapely pyclipper

   # Dành cho GPU:
   pip install onnxruntime-gpu opencv-python-headless numpy pillow pdfplumber shapely pyclipper
   ```
3. **Thực thi trực tiếp trong Python**:
   ```python
   from app.engine.manager import EngineManager
   from app.services.document_service import DocumentService

   # Khởi tạo EngineManager
   manager = EngineManager(models_dir="./models", device="auto")
   manager.initialize()

   doc_service = DocumentService(manager)

   with open("data/sample.pdf", "rb") as f:
       pdf_bytes = f.read()

   result = doc_service.extract_document(pdf_bytes, extract_tables=True)
   print("=== FULL MARKDOWN FOR RAG ===")
   print(result.full_markdown)
   ```

---

## 5. Chạy Kiểm Thử Tự Động (Testing)

```bash
cd backend
# Chạy toàn bộ 42 bài kiểm thử (unit & integration tests):
pytest -v

# Chạy kiểm thử với file ảnh thực tế trong thư mục img/:
python tests/verify_real_samples.py
```
