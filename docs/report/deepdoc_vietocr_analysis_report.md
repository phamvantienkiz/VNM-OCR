# Báo Cáo Phân Tích Hiện Trạng Mã Nguồn Deepdoc-VietOCR

> **Mã tài liệu:** `DOC-REP-OCR-001`  
> **Ngày cập nhật:** 25/08/2026  
> **Phiên bản:** `1.4.0` (Hoàn thiện toàn diện qua 4 vòng rà soát chuyên sâu, sẵn sàng 100% cho triển khai)  
> **Mục tiêu:** Đánh giá toàn diện mã nguồn hiện tại, bóc tách các điểm nghẽn kỹ thuật, import chain gây phình to dependency, mã rác thừa kế từ RAGFlow/DeepDoc và xác định yêu cầu chuẩn hóa thành dịch vụ FastAPI phục vụ bài toán RAG/Chatbot Document Ingestion.

---

## 1. Tổng quan Dự án & Bối cảnh Sử dụng

Dự án hiện tại là bản tùy biến kết hợp giữa **DeepDoc** (thuộc hệ sinh thái InfiniFlow/RAGFlow) và **VietOCR** nhằm phục vụ bài toán:
- Nhận dạng ký tự quang học (OCR) Tiếng Việt trên tài liệu scan / PDF.
- Nhận diện bố cục tài liệu (Document Layout Analysis - DLA qua YOLOv10 ONNX).
- Phân tích cấu trúc bảng (Table Structure Recognition - TSR qua YOLOv10 ONNX) để trích xuất bảng biểu sang định dạng Markdown.

Trong các pipeline RAG (Retrieval-Augmented Generation) và AI Agent/Chatbot hiện đại, bước **Document Parsing & OCR** là chặng tiền xử lý (ingestion) tối quan trọng. Nếu module này không được chuẩn hóa thành một microservice hoặc một package module độc lập, các dự án hạ tầng RAG khác sẽ gặp khó khăn khi tích hợp, dễ xung đột môi trường và không thể tái sử dụng linh hoạt.

---

## 2. Phân tích Chi tiết Cấu trúc & Các Vấn đề Hiện hữu

### 2.1 Cấu trúc Thư mục Hiện tại & Tình trạng Tạp nhiễm Mã nguồn

```
VNM-OCR/
├── conf/                # [RÁC] Chứa mapping RAGFlow, RSA private/public keys, service_conf.yaml thừa
├── docs/                # Tài liệu kỹ thuật, báo cáo phân tích & kế hoạch
│   ├── plan/
│   ├── product/
│   └── report/
├── models/              # [SIDE EFFECT] Cache HuggingFace/Torch tự sinh ra khi import module/__init__.py
├── module/              # Lõi xử lý OCR, Layout, TSR (bị dính chặt với utils cũ & import chain)
│   ├── layout_recognizer.py
│   ├── ocr.py           # OCR bản gốc PyTorch (chậm, nặng)
│   ├── ocr_onnx.py      # OCR bản ONNX Runtime (tối ưu, nhưng còn lỗi đường dẫn & import torch)
│   ├── operators.py     # Toán tử tiền xử lý ảnh
│   ├── postprocess.py   # DBPostProcess
│   ├── recognizer.py    # Lớp cơ sở Recognizer (bị phụ thuộc load_model từ ocr.py)
│   ├── seeit.py         # Helper vẽ bounding box
│   └── table_structure_recognizer.py
├── onnx/                # Chứa weights ONNX (cnn, det, encoder, decoder, layout, tsr)
├── ui/                  # Web demo UI (HTML/CSS/JS thuần)
├── utils/               # [NGUỒN GỐC DEPENDENCY HELL] MinIO, Redis, ES, Cryptodome, MySQL config...
├── vietocr/             # Thư mục clone mã nguồn VietOCR (lẫn cấu trúc import shadowing với package pip)
├── full_pipeline.py     # Script CLI trích xuất Layout + OCR + Bảng sang Markdown (đang dùng PyTorch OCR!)
├── server.py            # FastAPI server đơn giản (chỉ có 1 endpoint POST /api/ocr)
├── t_ocr.py             # Script test OCR
└── t_recognizer.py      # Script test Layout & TSR
```

---

### 2.2 Các Vấn đề Kiến trúc & Lỗi Kỹ thuật Nghiêm Trọng

#### ❌ Vấn đề 1: `utils/settings.py` — Nguồn Gốc Thực Sự của Dependency Hell
- Không đơn thuần là "rác nằm im trong repo", `utils/settings.py` **đang bị import trực tiếp** bởi các module lõi:
  - `module/ocr.py` (line 25): `from utils.settings import PARALLEL_DEVICES`
  - `module/ocr_onnx.py` (line 25): `from utils.settings import PARALLEL_DEVICES`
- Khi nạp `PARALLEL_DEVICES`, Python thực thi toàn bộ `utils/settings.py` -> kích hoạt `utils/__init__.py` -> bắt buộc import hàng loạt thư viện nặng:
  ```
  from module.ocr_onnx import OCR
    └── from utils.settings import PARALLEL_DEVICES
          └── from utils import get_base_config, decrypt_database_config (utils/__init__.py)
                └── import pycryptodomex, ruamel.yaml, elasticsearch, redis, minio, boto3, requests, etc.
  ```
- **Hệ quả:** Bắt buộc `requirements.txt` phải cài tất cả thư viện trên dù OCR chỉ cần lấy `torch.cuda.device_count()`.

---

#### ❌ Vấn đề 2: Lỗi Phân Tách Đường Dẫn Weights & Bẫy HuggingFace Fallback
- Xem [`module/ocr_onnx.py:405-438`](file:///E:/MyProject/VNM-OCR/module/ocr_onnx.py#L405-L438):
  ```python
  vietocr_weight_dir = os.path.join(get_project_base_directory(), "vietocr", "weight")
  model_dir = os.path.join(get_project_base_directory(), "onnx")
  
  self.text_detector = [TextDetector(model_dir, 0)]                  # onnx/det.onnx (Đúng)
  self.text_recognizer = [TextRecognizer(vietocr_weight_dir, 0)]     # vietocr/weight/cnn.onnx (SAI!)
  ```
- `TextRecognizer` yêu cầu tìm `cnn.onnx`, `encoder.onnx`, `decoder.onnx` trong thư mục truyền vào. Nhưng `vietocr/weight/` **chỉ chứa file `.pth`**, còn các file `.onnx` nằm ở `onnx/`.
- Khi nạp thất bại, code nhảy vào khối `except` và thực hiện **download toàn bộ repo HuggingFace `InfiniFlow/deepdoc` (~600MB)**.
- **Hệ quả:** 
  1. Nếu không có internet hoặc mạng chập chờn, service sẽ crash ngay lập tức.
  2. Lỗi logic đường dẫn bị che giấu, gây độ trễ khởi động bất thường do tải ngầm qua mạng.

---

#### ❌ Vấn đề 3: Sự Tồn Tại Song Song Hai Bản OCR (PyTorch vs ONNX) & Rủi Ro ở `full_pipeline.py`
- Dự án đang có 2 file OCR:
  - `module/ocr.py`: Dùng VietOCR PyTorch (`Predictor`), chạy nặng và chậm.
  - `module/ocr_onnx.py`: Dùng ONNX Runtime (`cnn.onnx`, `encoder.onnx`, `decoder.onnx`), chạy nhanh hơn nhiều.
- **Điểm nóng rủi ro:** File [`full_pipeline.py:17`](file:///E:/MyProject/VNM-OCR/full_pipeline.py#L17) và [`t_recognizer.py:30`](file:///E:/MyProject/VNM-OCR/t_recognizer.py#L30) đang import **`from module.ocr import OCR`** (bản PyTorch), trong khi `server.py` lại dùng bản ONNX.
- **Hệ quả:** Nếu port pipeline bóc tách văn bản + bảng biểu từ `full_pipeline.py` mà không chuyển đổi triệt để sang ONNX, hệ thống sẽ tiếp tục bị ràng buộc nặng nề vào PyTorch runtime.

---

#### ❌ Vấn đề 4: Buộc Phải Import PyTorch Chỉ Để Lấy Vocabulary Decoder (Và Cơ Chế Token Offset `+4`)
- Trong [`module/ocr_onnx.py:43-53`](file:///E:/MyProject/VNM-OCR/module/ocr_onnx.py#L43-L53):
  ```python
  config = Cfg.load_config_from_name('vgg_seq2seq')
  config['cnn']['pretrained']=False
  config['device'] = 'cpu'
  model, vocab = build_model(config)
  ```
- Đoạn code `load_state_dict` đã được comment out, nhưng việc gọi `build_model(config)` vẫn tạo ra kiến trúc PyTorch model trống (~200MB RAM) chỉ để lấy đối tượng `vocab`.
- **Cơ chế Token Map của VietOCR ([`vietocr/model/vocab.py`](file:///E:/MyProject/VNM-OCR/vietocr/model/vocab.py)):**
  - Token `0`: `<pad>`
  - Token `1`: `<sos>` / `<go>`
  - Token `2`: `<eos>`
  - Token `3`: `*` (mask token)
  - Token `4+`: Bắt đầu danh sách ký tự thực tế (`c2i = {c: i + 4 ...}`, `i2c = {i + 4: c ...}`).
- **Hệ quả:** Nếu tự viết lại `vocab.py` mà dùng sai offset (ví dụ `i + 3`), toàn bộ ký tự giải mã ra sẽ bị dịch chuyển lệch 1 đơn vị (Off-by-one Decoding Bug). Chuẩn hóa `vocab.py` phải tuân thủ nghiêm ngặt offset **`+4`**.

---

#### ❌ Vấn đề 5: Khóa Phụ Thuộc Ngược từ `Recognizer` sang `ocr.py` (PyTorch)
- Trong [`module/recognizer.py:29`](file:///E:/MyProject/VNM-OCR/module/recognizer.py#L29):
  ```python
  from .ocr import load_model
  ```
- Lớp cơ sở `Recognizer` (lớp cha của cả `LayoutRecognizer` và `TableStructureRecognizer`) import hàm `load_model` từ `ocr.py`.
- **Hệ quả:** Bất cứ khi nào khởi tạo Layout Analysis hay Table Recognition, Python đều bắt buộc load `ocr.py` (kéo theo PyTorch và VietOCR Predictor), phá vỡ tính độc lập của các module con. Cần tách `model_loader.py` độc lập.

---

#### ❌ Vấn đề 6: Label Bị Trùng Lặp trong `LayoutRecognizer4YOLOv10` & Yêu Cầu Xác Thực
- Trong [`module/layout_recognizer.py:170-181`](file:///E:/MyProject/VNM-OCR/module/layout_recognizer.py#L170-L181):
  ```python
  labels = [
      "title", "Text", "Reference", "Figure", 
      "Figure caption", "Table", "Table caption",
      "Table caption",        # ← Trùng lặp (Index 6 và 7)
      "Equation", 
      "Figure caption",       # ← Trùng lặp (Index 4 và 9)
  ]
  ```
- **Hệ quả & Giải pháp:** Không tự ý đặt tên nhãn mới mà chưa qua kiểm chứng thực nghiệm. Cần đưa vào **Quy trình Xác thực Nhãn (Validation Protocol)**:
  1. Đọc metadata trực tiếp từ file `layout.onnx` (`session.get_modelmeta().custom_metadata_map`).
  2. Chạy thử nghiệm phân loại trên tập mẫu 10-20 tài liệu đa dạng để đếm phân phối class IDs, đối chiếu training label map gốc của InfiniFlow DeepDoc trước khi chốt nhãn vào `LAYOUT_LABELS`.

---

#### ❌ Vấn đề 7: Xung Đột Gói `onnxruntime` vs `onnxruntime-gpu` và Giải Pháp Kiến Trúc Package
- Hai thư viện `onnxruntime` và `onnxruntime-gpu` dùng chung Python namespace `onnxruntime` và **xung đột trực tiếp** nếu cài đặt cùng lúc vào cùng môi trường.
- Nếu đặt `onnxruntime` ở base `dependencies` và `onnxruntime-gpu` ở `[gpu]` extra, lệnh `pip install .[gpu]` sẽ cài **cả hai gói**, dẫn đến lỗi namespace không xác định.
- **Hệ quả & Giải pháp:** Loại `onnxruntime` ra khỏi base `dependencies`, tách bạch rõ ràng thành 2 group tùy chọn:
  - `[cpu]`: Cài `"onnxruntime>=1.16.3"`
  - `[gpu]`: Cài `"onnxruntime-gpu>=1.16.3"`

---

## 3. Bảng Tổng Hợp So Sánh Hiện Trạng & Yêu Cầu Đích

| Tiêu chí | Trạng thái Hiện tại | Trạng thái Sau khi Chuẩn hóa (Target) |
| :--- | :--- | :--- |
| **Cấu trúc Thư mục** | Flat, lẫn lộn scripts, rác RAGFlow, web UI ở root | Chuẩn `backend/` theo `fastapi-backend-scaffold`, phân lớp Router / Service / Engine / Schemas |
| **Inference Framework** | Hỗn hợp (Server dùng ONNX, Full Pipeline dùng PyTorch) | **100% Thuần ONNX Runtime** cho toàn bộ OCR, Layout và TSR |
| **Phụ thuộc PyTorch trong Runtime** | Bắt buộc (do import chain và vocab extraction) | **Loại bỏ PyTorch khỏi Production**, chuyển sang standalone `vocab.py` (offset `+4` chuẩn) |
| **Quản lý Dependencies** | `requirements.txt` gom chung gây xung đột CPU/GPU | `pyproject.toml` tách độc lập: `[cpu]`, `[gpu]`, `[pdf]`, `[dev]`, nới lỏng `numpy>=1.23.0` |
| **Kích thước Docker Image** | ~5-6 GB (chứa PyTorch, CUDA, RAGFlow libs) | **~1-1.5 GB** (tinh gọn, chỉ chứa ONNX Runtime, OpenCV, NumPy, FastAPI) |
| **Tính Độc Lập / Portability** | Bị khóa chặt bởi `utils.settings` và `sys.path` | Đóng gói gọn trong `app/engine/`, có thể copy-paste sang project khác chạy ngay |
| **Khởi tạo & Quản lý Model** | Phân tán, global import-time instantiation | Model Registry Singleton, quản lý qua FastAPI `lifespan` (warmup & memory shrink) |
| **Khả năng Phục Vụ RAG** | Chỉ có 1 endpoint OCR ảnh đơn thô | Full Pipeline: PDF đa trang -> Layout Detection -> OCR -> TSR Table to Markdown -> Full Markdown |
| **Định dạng Dữ liệu (Schema)** | Nested List/Tuple không định kiểu | Pydantic v2 Models rõ ràng, sinh Swagger Docs OpenAPI tự động |

---

## 4. Kết luận Đánh Giá

Các vấn đề kỹ thuật của dự án đã được bóc tách và đối chiếu hoàn thiện qua 4 vòng rà soát chuyên sâu (bao gồm cấu trúc offset token `+4`, quy trình xác thực nhãn layout, namespace package ONNX, và import chain). Cốt lõi của việc tái cấu trúc là **độc lập hóa toàn bộ engine xử lý, chuyển đổi sang thuần ONNX Runtime với bộ giải mã từ vựng chuẩn xác và kiến trúc package không xung đột**, tạo ra một microservice chuyên nghiệp, tinh gọn, tốc độ cao và hoàn hảo cho các bài toán RAG/Chatbot.
