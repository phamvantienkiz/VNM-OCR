<p align="center">
  <a href="./README.md">Tiếng Việt</a> |
  <a href="./README_en.md">English</a> |
</p>

# *Deep*Doc + VietOCR - Công cụ OCR cho tiếng Việt nhanh và tiết kiệm chi phí

- [1. Giới thiệu](#1)
- [2. Kiến trúc kỹ thuật](#2)
- [3. Cài đặt và chạy thử](#3)
- [4. Nguồn gốc & Bản quyền (License & Origin)](#4)

<a name="1"></a>

## 1. Giới thiệu

Với một loạt tài liệu từ nhiều nguồn khác nhau với nhiều định dạng khác nhau và cùng với các yêu cầu truy xuất đa dạng, một công cụ trích xuất chính xác là rất cần thiết với bất kỳ doanh nghiệp nào. Dự án này giới thiệu công cụ DeepDoc, một công cụ OCR rất nhanh và tiết kiệm chi phí khi chỉ cần chạy trên CPU. Không những vậy còn có các tính năng kèm theo là Layout Recognizer (nhận diện bố cục) và Table Structure Recognizer (nhận diện cấu trúc bảng) giúp giữ định dạng văn bản sau OCR.

Tuy nhiên DeepDoc chưa được chuẩn hóa cho tiếng Việt nên chúng tôi đã tích hợp VietOCR và bản chuyển đổi định dạng ONNX vào phần Text Recognizer để nhận dạng văn bản tiếng Việt tốt hơn.

Bạn có thể tham khảo DeepDoc phiên bản gốc tại [đây](https://github.com/infiniflow/ragflow/blob/main/deepdoc/README.md). DeepDoc bản chất là một phần xử lý dữ liệu cho luồng RAG thuộc dự án RAGFlow, việc tách ra thành một kho chứa riêng giúp việc tùy biến ứng dụng được thuận tiện hơn.

<a name="2"></a>

## 2. Kiến trúc kỹ thuật

### 2.1 OCR

Phần này DeepDoc sử dụng PaddleOCR - Công cụ mã nguồn mở rất thông dụng được phát triển bởi Baidu - sau khi chuyển sang ONNX. ONNX (Open Neural Network Exchange) là định dạng mở cho mô hình AI, giúp mô hình tương thích đa nền tảng, tối ưu tốc độ trên CPU/GPU và giảm chi phí hạ tầng khi triển khai.

Kiến trúc OCR PP-OCRv5 bao gồm 4 phần chính:

- **Image Preprocessing Module (Tiền xử lý ảnh)**: Cải thiện chất lượng ảnh, xử lý xoay/nghiêng bằng mô hình phân loại hướng (PP-LCNet) và unwarping (UVDoc).
- **Text Detection (Phát hiện văn bản)**: Nâng cấp từ PP-OCRv4 nhờ backbone PP-HGNetV2, distillation từ GOT-OCR2.0, và tăng cường dữ liệu. Giữ lại PFHead và DSR từ phiên bản trước.
- **Text Line Orientation Classification (Phân loại hướng dòng chữ)**: Tự động phát hiện, sửa hướng dòng chữ (ngược, xoay) để chuẩn bị cho bước nhận dạng.
- **Text Recognition (Nhận dạng văn bản)**: Kiến trúc 2 nhánh với PP-HGNetV2, huấn luyện bằng GTC-NRTR (attention) để hướng dẫn SVTR-HGNet (CTC, nhẹ, nhanh).

Chi tiết về PP-OCRv5, bạn có thể tham khảo tài liệu chính thức tại [đây](https://arxiv.org/html/2507.05595v1).

Phần Recognition của Paddle đã được thay bằng VietOCR và bản ONNX để nhận dạng chữ tiếng Việt chính xác hơn. Bạn có thể tìm hiểu thêm về VietOCR tại [đây](https://github.com/pbcquoc/vietocr). Phần chuyển đổi định dạng ONNX cho VietOCR được tham khảo từ bài viết [này.](https://viblo.asia/p/chuyen-doi-mo-hinh-hoc-sau-ve-onnx-bWrZnz4vZxw)

### 2.2 Layout Recognizer và Table Structure Recognizer

Phần này DeepDoc sử dụng YOLOv10 (You Only Look Once) phiên bản ONNX.
Kiến trúc gồm 3 phần chính:

- **Backbone**: Trích xuất đặc trưng từ ảnh, dùng thiết kế nhẹ và hiệu quả.
- **Neck**: Kết hợp đa cấp độ đặc trưng (FPN/PAN cải tiến) để phát hiện tốt cả vật thể nhỏ lẫn lớn.
- **Head**: Sử dụng Anchor-Free decoupled head (tách nhánh classification và regression), tăng độ chính xác và dễ huấn luyện.

Trong DeepDoc, YOLOv10 được huấn luyện để nhận dạng các loại nhãn sau:

- **Layout Recognizer (10 loại nhãn)**: Text (Văn bản), Title (Tiêu đề), Image (Hình ảnh), Image Caption (Chú thích hình ảnh), Table (Bảng), Table Caption (Chú thích bảng), Header (Đầu đề), Footer (Chân trang), Reference (Tài liệu tham khảo), Equation (Phương trình).
- **Table Structure Recognizer (5 loại nhãn)**: Column (Cột), Row (Hàng), Column header (Đầu đề cột), Projected row header (Đầu đề hàng được chiếu), Spanning cell (Ô trải dài).

Chi tiết về YOLOv10 tham khảo tại [đây](https://arxiv.org/pdf/2405.14458).

<a name="3"></a>

## 3. Cài đặt và chạy thử

### 3.1. Cài đặt môi trường

Đầu tiên clone mã nguồn về máy:

```bash
git clone https://github.com/hoaivannguyen/deepdoc_vietocr.git
cd deepdoc_vietocr
```

Tạo và kích hoạt môi trường ảo (Virtual Environment) để quản lý dependencies độc lập:

```bash
python -m venv .venv
# Trên Windows:
.\.venv\Scripts\activate
# Trên Linux/macOS:
source .venv/bin/activate
```

Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

### 3.2. Sử dụng dòng lệnh (CLI)

#### Chạy OCR nhận dạng chữ:

```bash
python t_ocr.py --inputs=path_to_images_or_pdfs --output_dir=path_to_store_result
```

_Đầu vào có thể là một thư mục chứa ảnh/PDF hoặc đường dẫn cụ thể của một file. Kết quả xuất ra gồm file ảnh vẽ bounding box và file `.txt` chứa văn bản._

#### Chạy nhận diện Bố cục (Layout) & Cấu trúc Bảng (TSR):

```bash
# Layout Recognizer
python t_recognizer.py --inputs=path_to_images_or_pdfs --threshold=0.2 --mode=layout --output_dir=path_to_store_result

# Table Structure Recognizer (TSR)
python t_recognizer.py --inputs=path_to_images_or_pdfs --threshold=0.2 --mode=tsr --output_dir=path_to_store_result
```

### 3.3. Chạy thử Giao diện trực quan (Visual Testing Web UI)

Để chạy thử trực quan trên giao diện Web Dashboard, bạn khởi chạy máy chủ backend API tích hợp sẵn:

```bash
python server.py
```

Sau đó truy cập địa chỉ **`http://127.0.0.1:8000/`** trên trình duyệt của bạn. Bạn có thể kéo thả tài liệu ảnh/PDF trực tiếp để chạy OCR và xem trực quan kết quả tọa độ chữ khi hover chuột.

<a name="4"></a>

## 4. Nguồn gốc & Bản quyền (License & Origin)

### 4.1. Nguồn gốc & Tri ân (Repository Origin & Acknowledgements)

Dự án này là một phiên bản cải tiến sâu, tối ưu hóa cấu trúc và phát triển mở rộng chuyên sâu dựa trên kho lưu trữ mã nguồn:

- **deepdoc_vietocr** (phát triển bởi [hoaivannguyen](https://github.com/hoaivannguyen/deepdoc_vietocr)).

Hệ thống kế thừa và tích hợp các cấu phần công nghệ cốt lõi từ các dự án mã nguồn mở uy tín sau:

1.  **DeepDoc / RAGFlow** (phát triển bởi [InfiniFlow](https://github.com/infiniflow/ragflow) dưới giấy phép _Apache 2.0_): Nền tảng xử lý layout, định vị bảng (table recognition) và PDF parser.
2.  **VietOCR** (phát triển bởi tác giả [pbcquoc](https://github.com/pbcquoc/vietocr) dưới giấy phép _Apache 2.0_): Bộ thư viện và mô hình nhận diện ký tự quang học (OCR) cho ngôn ngữ tiếng Việt.

_Chúng tôi bày tỏ lòng tôn trọng và sự tri ân sâu sắc đến các tác giả và cộng đồng đã phát triển các dự án gốc nêu trên._

### 4.2. Giấy phép bản quyền & Giới hạn Phi thương mại (License & Non-Commercial Restriction)

Để bảo vệ đóng góp của cộng đồng và chất xám của đội ngũ phát triển, dự án này được phát hành dưới hình thức **Giấy phép Nguồn mở Giới hạn Phi thương mại**, áp dụng cụ thể như sau:

#### A. Đối với Mã nguồn (Source Code)

Mã nguồn của dự án áp dụng **Giấy phép Apache 2.0 kết hợp Điều khoản bổ sung cấm thương mại (Apache License 2.0 with Commons Clause)**:

- **Giữ nguyên bản quyền gốc:** Tất cả các thông tin bản quyền, tiêu đề (headers) của tác giả gốc ở đầu mỗi tệp tin mã nguồn thuộc về dự án Ragflow/DeepDoc và VietOCR phải được giữ nguyên vẹn.
- **Quyền sửa đổi & Chia sẻ:** Bạn được quyền xem, sao chép, sửa đổi và phân phối lại mã nguồn này cho các mục đích học tập, giảng dạy, nghiên cứu học thuật hoặc sử dụng nội bộ phi lợi nhuận.
- **CẤM THƯƠNG MẠI HÓA (Commons Clause):** **Nghiêm cấm tuyệt đối** việc sử dụng, sao chép, sửa đổi, hoặc phân phối phần mã nguồn này (bao gồm cả các phần sửa đổi dựa trên nó) cho bất kỳ mục đích thương mại nào dưới mọi hình thức. Điều này bao gồm nhưng không giới hạn ở việc: bán phần mềm, đóng gói thành sản phẩm thương mại độc quyền, hoặc sử dụng để cung cấp dịch vụ đám mây có thu phí (SaaS/API thương mại).

#### B. Đối với Trọng số Mô hình (Model Weights)

Tất cả các tệp trọng số mô hình (Model Weights/Checkpoints) được finetune và phát hành từ dự án này được bảo hộ nghiêm ngặt dưới giấy phép quốc tế: **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.

- Bạn bắt buộc phải ghi công (Attribution) dự án này và các tác giả gốc khi sử dụng mô hình.
- Không được phép sử dụng mô hình này vào bất kỳ hoạt động thương mại hoặc tạo ra doanh thu nào.
- Nếu bạn tiếp tục finetune hoặc cải tiến mô hình từ trọng số của chúng tôi, bạn bắt buộc phải chia sẻ kết quả dưới cùng giấy phép cấm thương mại này (ShareAlike).

#### C. Tuyên bố miễn trừ trách nhiệm

Trừ khi được yêu cầu bởi luật áp dụng hoặc được đồng ý bằng văn bản, phần mềm và mô hình được phân phối theo cơ sở **"CÓ SẴN (AS IS)"**, **KHÔNG CÓ BẤT KỲ BẢO ĐẢM HOẶC ĐIỀU KIỆN NÀO**, dù là rõ ràng hay ngầm định về hiệu năng hoặc độ chính xác.

_Chi tiết xem tại [LICENSE](LICENSE)_

---

## Tài liệu tham khảo

- RAGFlow GitHub: https://github.com/infiniflow/ragflow
- PP-OCRv5: https://arxiv.org/html/2507.05595v1
- VietOCR GitHub: https://github.com/pbcquoc/vietocr
- VietOCR ONNX: https://viblo.asia/p/chuyen-doi-mo-hinh-hoc-sau-ve-onnx-bWrZnz4vZxw
- YOLOv10: https://arxiv.org/pdf/2405.14458
