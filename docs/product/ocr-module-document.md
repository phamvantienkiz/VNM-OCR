# Tài liệu Kỹ thuật & Hướng dẫn Tích hợp Mô-đun OCR (ocr_modules)

Tài liệu này cung cấp thông tin chi tiết về mặt kiến trúc, các cải tiến hiệu năng, cấu trúc API, và hướng dẫn dành cho lập trình viên để tích hợp mô-đun nhận dạng ký tự tiếng Việt (OCR) vào hệ thống số hóa tài liệu tổng thể.

---

## 1. Tổng quan Cấu trúc Thư mục Dự án

Cấu trúc phân cấp của thư mục `ocr_modules` và vị trí của các cấu phần cốt lõi được mô tả dưới đây:

```
ocr_modules/
├── models/
│   └── .cache/          # Thư mục cache cục bộ chứa Hugging Face & Torch Hub weights (đã được cách ly)
├── module/              # Mã nguồn xử lý lõi của mô-đun
│   ├── __init__.py      # Khởi tạo mô-đun, thiết lập các biến môi trường cách ly (HF_HOME, TORCH_HOME)
│   ├── layout.py        # Xử lý nhận dạng bố cục (YOLOv10 ONNX)
│   ├── ocr.py           # Bộ điều phối OCR phiên bản gốc (PyTorch)
│   ├── ocr_onnx.py      # Bộ điều phối OCR tối ưu hóa (ONNX Runtime)
│   ├── operators.py     # Lớp toán tử tiền xử lý ảnh (Resize, Chuẩn hóa, CHW Convert)
│   ├── postprocess.py   # Lớp hậu xử lý DBPostProcess (Chuyển đổi heatmap thành bounding box)
│   └── tsr.py           # Xử lý nhận dạng cấu trúc bảng (YOLOv10 ONNX)
├── onnx/                # Thư mục chứa các tệp trọng số mô hình ONNX
│   ├── cnn.onnx         # Khối trích xuất đặc trưng ảnh (CNN) của VietOCR
│   ├── encoder.onnx     # Khối Encoder Sequence của VietOCR
│   ├── decoder.onnx     # Khối Decoder Sequence (Autoregressive Decoder) của VietOCR
│   ├── det.onnx         # Mô hình phát hiện dòng chữ (Text Detection - PP-OCRV5)
│   └── layout.onnx      # Mô hình nhận diện bố cục (YOLOv10)
├── ui/                  # Giao diện chạy thử trực quan (Visual Testing Frontend)
│   ├── index.html       # Giao diện HTML5 thiết kế theo chuẩn Geist, tuân thủ WCAG 2.2 AA
│   ├── style.css        # CSS tùy biến bố cục Dashboard (50/50 split-view, Sticky Footer)
│   └── app.js           # Xử lý client-side PDF rendering (PDF.js) và chia tỷ lệ tọa độ hộp thoại
├── vietocr/             # Cấu hình ánh xạ từ vựng và tham chiếu lớp VietOCR
│   ├── tool/
│   │   ├── config.py    # Quản lý cấu hình vocabulary và mô hình
│   │   └── translate.py # Xử lý chuyển dịch token-to-text
│   └── weight/
│       └── config.yaml  # Tệp cấu hình siêu tham số (Hyperparameters) cho mô hình Seq2Seq/Transformer
├── pyproject.toml       # Tệp cấu hình đặc tả dependencies của dự án
├── requirements.txt     # Danh sách các gói phụ thuộc đã biên dịch (Lockfile)
├── server.py            # Máy chủ API (FastAPI + Uvicorn) phục vụ Visual Testing
├── t_ocr.py             # Script CLI chạy kiểm thử pipeline OCR
└── t_recognizer.py      # Script CLI chạy kiểm thử Layout/TSR
```

---

## 2. Kiến trúc Hoạt động & Bản đồ Phụ thuộc (Dependency Map)

### 2.1 Luồng Xử lý Dữ liệu OCR (Data Flow Diagram)

Khi một tệp tin hình ảnh được gửi vào hệ thống OCR, luồng xử lý sẽ đi qua 3 giai đoạn chính: **Phát hiện (Detection) -> Cắt & Chuẩn hóa (Crop & Normalize) -> Nhận diện (Recognition)**.

```
[Ảnh Đầu Vào]
     │
     ▼
┌────────────────────────────────────────────────────────┐
│ 1. Text Detector (PP-OCRV5 - det.onnx)                 │
│    - Tiền xử lý: Resize (960px), Normalize, CHW        │
│    - Chạy Inference Session trên ONNX Runtime          │
│    - Hậu xử lý: DBPostProcess (Heatmap -> Polygons)     │
└────┬───────────────────────────────────────────────────┘
     │
     ├─► [Danh sách các Bounding Boxes]
     │
     ▼
┌────────────────────────────────────────────────────────┐
│ 2. Sắp xếp & Cắt ảnh (OCR Orchestrator)                │
│    - Sắp xếp hộp thoại từ trên xuống, trái sang phải   │
│    - Perspective Transform cắt ảnh xoay nghiêng        │
│    - Resize ảnh đã cắt về chiều cao chuẩn 32px         │
└────┬───────────────────────────────────────────────────┘
     │
     ├─► [Mảng ảnh dòng chữ chuẩn hóa (Height 32px)]
     │
     ▼
┌────────────────────────────────────────────────────────┐
│ 3. Text Recognizer (VietOCR ONNX)                      │
│    - CNN session: Trích xuất đặc trưng từ ảnh 32px     │
│    - Encoder session: Mã hóa chuỗi đặc trưng          │
│    - Decoder session: Dịch tự hồi quy (Autoregressive)  │
│    - Bản đồ từ vựng (Vocab): Token ID -> Chữ Tiếng Việt │
└────┬───────────────────────────────────────────────────┘
     │
     ▼
[Kết quả đầu ra dạng Tuple: (Tọa độ 4 góc, Dòng chữ, Độ tin cậy)]
```

### 2.2 Bản đồ Phụ thuộc Hàm & Module (Function Dependency Map)

Dưới đây là sơ đồ thể hiện mối quan hệ gọi hàm giữa các tệp nguồn trong dự án:

```
t_ocr.py (CLI) OR server.py (FastAPI)
  │
  └──► module.ocr_onnx.OCR.__call__()  [Bộ điều phối chính]
        │
        ├──► module.ocr_onnx.OCR.detect()
        │     │
        │     └──► module.ocr_onnx.TextDetector.__call__()
        │           │
        │           ├──► module.ocr_onnx.transform() 
        │           │     └──► module.operators (Resize, Normalize)
        │           │
        │           ├──► onnxruntime.InferenceSession.run("det.onnx")
        │           │
        │           └──► module.postprocess.DBPostProcess.__call__()
        │
        ├──► module.ocr_onnx.OCR.sorted_boxes() [Sắp xếp thứ tự đọc]
        │
        ├──► module.ocr_onnx.OCR.get_rotate_crop_image() [Cân chỉnh perspective]
        │
        └──► module.ocr_onnx.OCR.recognize_batch()
              │
              └──► module.ocr_onnx.TextRecognizer.__call__()
                    │
                    ├──► onnxruntime.InferenceSession.run("cnn.onnx")
                    ├──► onnxruntime.InferenceSession.run("encoder.onnx")
                    ├──► module.ocr_onnx.translate_onnx() [Vòng lặp tự hồi quy]
                    │     └──► onnxruntime.InferenceSession.run("decoder.onnx")
                    │
                    └──► vietocr.tool.config.vocab.decode() [Giải mã token ra chữ Việt]
```

---

## 3. Phân tích Chi tiết Khối Xử lý Lõi (Core Classes & Core Dependencies)

### 3.1 Khối Phát hiện Văn bản: `TextDetector`
*   **Mục đích**: Nhận đầu vào là ảnh màu gốc, tìm kiếm tọa độ phân vùng có chứa chữ.
*   **Cơ chế hoạt động**:
    1.  **Tiền xử lý (`preprocess_op`)**: Khởi tạo danh sách các toán tử từ `module/operators.py`.
        *   `DetResizeForTest`: Đưa ảnh về kích thước tối đa 960px để giữ cân bằng tốc độ suy luận.
        *   `NormalizeImage`: Chuẩn hóa điểm ảnh theo phân phối chuẩn Gaussian (mean, std).
        *   `ToCHWImage`: Chuyển đổi định dạng layout mảng từ HWC (Height, Width, Channel) sang CHW.
    2.  **Chạy Inference**: Nạp mô hình `onnx/det.onnx` thông qua hàm `load_model()`. Thực hiện suy luận để lấy bản đồ xác suất ký tự (probability heatmap).
    3.  **Hậu xử lý (`postprocess_op`)**: Sử dụng thuật toán DBPostProcess (`module/postprocess.py`) để gom cụm các pixel có độ tin cậy > 0.3 thành các đa giác 4 góc (quadrilateral polygons).
    4.  **Lọc nhiễu**: Lọc bỏ các bounding box có kích thước chiều ngang hoặc chiều dọc nhỏ hơn hoặc bằng 3 pixel thông qua hàm `filter_tag_det_res()`.

### 3.2 Khối Nhận dạng Văn bản: `TextRecognizer`
*   **Mục đích**: Nhận đầu vào là danh sách các ảnh dòng chữ đã cắt, trả về văn bản Tiếng Việt dạng chuỗi Unicode.
*   **Cơ chế hoạt động**:
    1.  **Chuẩn hóa kích thước**: Đưa mọi dòng chữ đã cắt về chiều cao cố định 32px, chiều rộng thay đổi theo tỷ lệ khung hình dòng chữ thô. Chuyển đổi sang hệ màu xám/RGB chuẩn hóa trong khoảng `[0.0, 1.0]`.
    2.  **Inference cnn & encoder**: Chạy qua `cnn.onnx` để trích xuất đặc trưng hình ảnh. Tiếp theo, chuỗi đặc trưng được đi qua `encoder.onnx` để biểu diễn dưới dạng vector ẩn (hidden states).
    3.  **Dịch tự hồi quy (`translate_onnx`)**:
        *   Bắt đầu với mã Token SOS (`sos_token = 1`).
        *   Chạy vòng lặp (loop): Gửi Token trước đó và vector ẩn của encoder vào `decoder.onnx` để dự đoán xác suất Token tiếp theo thông qua hàm toán tử `torch.topk`.
        *   Vòng lặp dừng lại khi gặp mã Token EOS (`eos_token = 2`) hoặc vượt quá độ dài tối đa cho phép (`max_seq_length = 128`).
    4.  **Giải mã (`vocab.decode()`)**: Đối chiếu chuỗi mã Token ID nhận được với bảng từ vựng (Vocabulary Map) của `vietocr` để dịch ngược thành văn bản Unicode UTF-8 hoàn chỉnh.

### 3.3 Khối Điều phối: `OCR`
*   **Mục đích**: Quản lý thiết bị phần cứng, chạy pipeline tuần tự và sắp xếp văn bản theo luồng đọc tự nhiên của con người.
*   **Sắp xếp hộp văn bản (`sorted_boxes`)**:
    *   Sắp xếp toàn bộ danh sách bounding box theo thứ tự tọa độ Y tăng dần (từ trên xuống dưới).
    *   Nếu hai dòng chữ nằm trên cùng một dòng ngang (chênh lệch tọa độ Y nhỏ hơn 10 pixel), sắp xếp chúng theo tọa độ X tăng dần (từ trái qua phải). Điều này đảm bảo trích xuất đúng định dạng văn bản nhiều cột.

---

## 4. Các Phụ thuộc của Tệp Lõi (Core Files Dependencies)

Dự án duy trì các phụ thuộc cực kỳ tinh gọn để giảm thiểu xung đột thư viện:

| Tệp lõi / Thư mục | Thư viện bên ngoài (External Dependencies) | Vai trò trong hệ thống |
| :--- | :--- | :--- |
| **`module/ocr_onnx.py`** | `onnxruntime` (hoặc `onnxruntime-gpu`), `opencv-python-headless`, `numpy`, `torch` | Tệp lõi điều phối toàn bộ luồng xử lý OCR trên ONNX Runtime. |
| **`module/operators.py`** | `numpy`, `opencv-python-headless` | Cung cấp các phép toán xử lý ảnh số trực tiếp trên mảng NumPy. |
| **`module/postprocess.py`** | `shapely`, `pyclipper`, `numpy` | Thực hiện các phép toán hình học đa giác để khoanh vùng chữ. |
| **`vietocr/`** | `vietocr` (được cài đặt qua pip) | Cung cấp logic giải mã từ vựng (`vietocr.tool`). |
| **`server.py`** | `fastapi`, `uvicorn`, `python-multipart` | Khởi chạy máy chủ API để phục vụ frontend. |

---

## 5. Hướng dẫn Tích hợp Code (Developer Guide)

### 5.1 Sử dụng trực tiếp trong mã nguồn Python (Python API)
Lập trình viên có thể import lớp `OCR` từ gói `module.ocr_onnx` để chạy trích xuất ký tự:

```python
import os
import sys
import cv2
import numpy as np

# Đảm bảo đường dẫn import trỏ đúng vào thư mục ocr_modules
sys.path.insert(0, "/path/to/ocr_modules")

from module.ocr_onnx import OCR

# 1. Khởi tạo thực thể OCR (Nạp các mô hình ONNX vào RAM)
ocr_engine = OCR()

# 2. Đọc ảnh đầu vào bằng giải pháp tương thích Unicode
img_path = "path/to/tài_liệu_của_bạn.jpg"
img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)

if img is not None:
    # 3. Chạy suy luận OCR
    # Kết quả trả về là một danh sách các phần tử chứa tọa độ hộp và văn bản tương ứng
    results = ocr_engine(img)
    
    for box, (text, score) in results:
        print(f"Tọa độ hộp thoại: {box}")
        print(f"Văn bản trích xuất: '{text}' (Độ tin cậy: {score:.2f})")
        print("-" * 30)
```

### 5.2 Giải thích định dạng dữ liệu đầu ra (Output Schema)
Kết quả trả về của hàm gọi mô hình `results = ocr_engine(img)` là một danh sách các Tuple:
`List[Tuple[List[List[int]], Tuple[str, float]]]`

Chi tiết phân cấp:
```json
[
  [
    [[x1, y1], [x2, y2], [x3, y3], [x4, y4]], // Tọa độ 4 góc của bounding box (dạng mảng số nguyên)
    ["Nội dung dòng văn bản nhận dạng được", 0.9854] // Văn bản Unicode UTF-8 và xác suất tin cậy (0.0 -> 1.0)
  ],
  ...
]
```

---

## 6. Máy chủ API & Giao diện Chạy thử (FastAPI & Web UI)

Dự án cung cấp sẵn một máy chủ FastAPI nhẹ để hỗ trợ việc chạy thử nghiệm trực quan qua giao diện đồ họa.

### 6.1 Tài liệu API Điểm cuối (API Endpoints)
#### **`POST /api/ocr`**
*   **Mô tả**: Nhận diện ký tự từ tệp ảnh tải lên.
*   **Định dạng yêu cầu (Request Format)**: `multipart/form-data`
    *   Tham số: `file` (dạng Binary File - JPG, PNG, WEBP, BMP, v.v.)
*   **Định dạng phản hồi (Response Format)**: `JSON`
    *   Mẫu dữ liệu trả về thành công:
        ```json
        [
          [[[32, 15], [200, 15], [200, 40], [32, 40]], ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", 0.9982]],
          [[[32, 45], [150, 45], [150, 65], [32, 65]], ["Độc lập - Tự do - Hạnh phúc", 0.9915]]
        ]
        ```

### 6.2 Khởi chạy Server
Lập trình viên có thể khởi chạy server demo cục bộ thông qua lệnh:
```powershell
.\.venv\Scripts\python.exe server.py
```
*   Máy chủ API và giao diện Web tĩnh sẽ được host tại địa chỉ: **`http://127.0.0.1:8000/`**
*   Giao diện hỗ trợ kéo thả trực tiếp tệp PDF/ảnh, tự động phân tích và hiển thị kết quả song song trực quan 50/50, cho phép di chuột (hover) trên ảnh gốc để xem nội dung hộp văn bản tương ứng.
