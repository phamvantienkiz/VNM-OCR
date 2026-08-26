# KẾ HOẠCH TÁI THIẾT KẾ & NÂNG CẤP GIAO DIỆN UI (3-COLUMN LAYOUT)
## HỆ THỐNG NHẬN DẠNG KÝ TỰ QUANG HỌC TIẾNG VIỆT (VIETNAMESE OCR DEMO)

> **Mã tài liệu:** `DOC-PLAN-UI-001`  
> **Phiên bản:** `1.4.1` (Final Production Ready — Đã thẩm định toàn diện qua 9 vòng Counter-Review & Full Codebase Verification)  
> **Ngày cập nhật:** 27/08/2026  
> **Trạng thái:** Verified & Production Ready / Sẵn sàng triển khai  
> **Tham chiếu đối chiếu:**
> - [`DOC-REP-OCR-002 v9.0.0`](file:///E:/MyProject/VNM-OCR/docs/report/counter_argument_review.md) — Báo cáo Counter-Review (Đã xử lý trọn vẹn #25–#61)
> - [`DOC-PLAN-OCR-001 v1.4.0`](file:///E:/MyProject/VNM-OCR/docs/plan/fastapi_backend_refactoring_plan.md) — Kế hoạch chuẩn hóa backend FastAPI
> - [`ui/design.md`](file:///E:/MyProject/VNM-OCR/ui/design.md) — Quy chuẩn Design Tokens & UI/UX Standards
> - Mã nguồn Backend: [`backend/app/api/v1/`](file:///E:/MyProject/VNM-OCR/backend/app/api/v1/), [`backend/app/services/`](file:///E:/MyProject/VNM-OCR/backend/app/services/), [`backend/app/utils/`](file:///E:/MyProject/VNM-OCR/backend/app/utils/) & [`backend/app/exceptions/`](file:///E:/MyProject/VNM-OCR/backend/app/exceptions/)

---

## 1. Bối cảnh & Mục tiêu dự án

### 1.1. Bối cảnh
Sau khi hệ thống OCR lõi được tái cấu trúc thành công sang mô hình Microservice / Backend FastAPI chuẩn mực (`backend/` với đầy đủ các endpoint `/api/v1/ocr`, `/api/v1/layout`, `/api/v1/table`, `/api/v1/document/extract`), giao diện web demo ban đầu trong thư mục `ui/` bộc lộ các hạn chế lớn:
1. **Trải nghiệm người dùng (UX) bị gián đoạn**: Sidebar đen tĩnh chiếm nhiều diện tích; khi tải tệp lên thì khu vực Upload bị ẩn hoàn toàn, chuyển màn hình khiến việc đổi tệp hoặc thử nghiệm cấu hình mới rất rườm rà.
2. **Cấu trúc dữ liệu API chưa đồng bộ**: Mã JavaScript cũ (`app.js`) phân tích dữ liệu dạng mảng lồng nhau cũ (`item[0]`, `item[1][0]`), chưa tương thích trực tiếp với Schema Pydantic V2 mới của FastAPI (`OCRResponse`, `OCRLineResult`, `DocumentExtractionResponse`, `LayoutResponse`).
3. **Thiếu tính linh hoạt & khả năng tương tác trực quan**: Bố cục cũ chật chội, thiếu công cụ tương tác (Zoom/Pan ảnh mượt mà, đồng bộ highlight 2 chiều giữa Bounding Box và dòng văn bản, chuyển trang PDF kèm thumbnail).

### 1.2. Mục tiêu thiết kế mới
- **Kiến trúc 3 Cột (3-Column Layout) đồng bộ trên cùng một màn hình**:
  - **Cột 1 (Bên trái - 25%)**: Tải tệp (PDF/Image), cấu hình tham số suy luận (`extract_tables`, `resolution`), chọn Endpoint và danh sách thumbnail trang tài liệu.
  - **Cột 2 (Ở giữa - 45%)**: Trình xem trước tài liệu (Document Viewer) kèm lớp phủ Bounding Box hỗ trợ cả 4-point polygon và 4-float rectangle, có khả năng phóng to/thu nhỏ (Zoom/Pan), đồng bộ DPI động với backend và tương tác phản hồi.
  - **Cột 3 (Bên phải - 30%)**: Hiển thị kết quả văn bản trích xuất (Raw Text / Markdown & Structured Lines), thống kê hiệu năng (độ trễ, độ tin cậy) và các công cụ xuất dữ liệu (Sao chép, Tải TXT/JSON/MD).
- **Công nghệ tinh gọn, không phụ thuộc build tool**: Sử dụng thuần **HTML5**, **Bootstrap 5.3 (CDN)** kết hợp **Custom CSS Grid / Design Tokens** (tuân thủ `ui/design.md`), và **Modular JavaScript (ES6)**.
- **Tương thích cao & Khớp 100% API Contract & Runtime**: Hoạt động trực tiếp qua Static File Mount của FastAPI (`http://localhost:8000/ui/index.html`) hoặc bất kỳ Live Server nào; hỗ trợ đầy đủ responsive, accessibility (WCAG 2.2 AA), đồng bộ DPI render, kiểm soát vòng đời request (`AbortController`) và quản lý bộ nhớ triệt để.

---

## 2. Phân tích hiện trạng & Điểm nghẽn (Gap Analysis)

| Hạng mục | Hiện trạng (`ui/` cũ) | Giải pháp mới (3-Column Redesign v1.4.0) |
| :--- | :--- | :--- |
| **Bố cục tổng thể** | Layout 2 vùng (Sidebar đen 260px + Content View thay đổi trạng thái) | **Layout 3 Cột song song CSS Grid** (25% / 45% / 30%) kèm Responsive Fallback đa tầng |
| **Quy trình tải tệp** | Upload ẩn đi sau khi chọn file, không thể drop file mới nhanh | Dropzone nhỏ gọn luôn hiển thị ở Cột 1; hỗ trợ kéo thả tệp mới bất kỳ lúc nào, validate dimension an toàn |
| **Xem trước PDF** | Chỉ có nút chuyển trang dạng text, không thấy tổng quan | Thumbnail list ở Cột 1; **Đồng bộ DPI render động** (`scale = dpi / 72`), quản lý Object URL sạch và cơ chế Eviction RAM |
| **Visual Bounding Box** | Vẽ div BBox tĩnh, dễ lệch tỷ lệ khi resize, không zoom/pan | Viewport **Zoom/Pan**, hàm `normalizeBbox()` hỗ trợ cả **4-point polygon** và **4-float rect** theo **pixel tuyệt đối** |
| **Hiển thị kết quả** | Chỉ có 1 ô `textarea` trích xuất toàn bộ text | **Tabs đa chế độ** có `aria-live`: Tab 1 (Raw Text / Full Markdown), Tab 2 (Line Details + Score), Tab 3 (Raw JSON) |
| **Đồng bộ 2 chiều** | BBox trên ảnh và Text độc lập, không có tương tác | **Event Bus pub/sub**: Hover/Click BBox tự highlight dòng text ở Cột 3 và ngược lại |
| **Vòng đời Request** | Không thể hủy request đang chạy khi đổi file/reset | **`AbortController` tích hợp**: Tự động hủy HTTP inflight request khi reset hoặc đổi file |
| **Tích hợp & Xử lý lỗi**| Gọi endpoint cũ `/api/ocr`, xử lý lỗi sơ sài | Gọi chuẩn REST API v1 (`/api/v1/ocr`, `/api/v1/document/extract`) với **Error Response Matrix** khớp 100% backend exceptions |

---

## 3. Kiến trúc Thiết kế UI/UX 3 Cột Chi tiết

```
+---------------------------------------------------------------------------------------------------------+
|                                        TOPBAR HEADER (Brand, Status API & Model Readiness, Mode)        |
+------------------------------------+------------------------------------+-------------------------------+
|  CỘT 1: UPLOAD & CẤU HÌNH (25%)   |   CỘT 2: DOCUMENT PREVIEW (45%)    |  CỘT 3: KẾT QUẢ OCR (30%)     |
+------------------------------------+------------------------------------+-------------------------------+
| [1.1] Drag & Drop Zone gọn gàng    | [2.1] Viewer Toolbar               | [3.1] Metrics Overview        |
|  - Hỗ trợ PDF, JPG, PNG, WEBP...   |  - Zoom In / Out / Reset / Fit     |  - Thời gian: 24.5 ms         |
|  - Dimension Guard (<= 8000px)     |  - BBox Toggle: On / Off           |  - Số dòng: 34                |
|  - File Info (Tên, Size, Định dạng)|  - Chuyển trang (PDF Page Nav)     |  - Độ tin cậy TB: 98.4%       |
|                                    |                                    |                               |
| [1.2] Pipeline & Cấu hình Options  | [2.2] Canvas / Image Viewport      | [3.2] Result View Tabs        |
|  - Mode: Single OCR / Document Ext |  - DPI-Synchronized Image Canvas   |  * Tab 1: [Raw / Markdown]    |
|  - Resolution (72/150/300 DPI)     |  - Normalized SVG/Canvas BBox Layer|  * Tab 2: [Line-by-Line List] |
|  - Extract Tables Toggle: On/Off   |  - Hover Tooltip (Score, Text)     |  * Tab 3: [JSON Response]     |
|  - Confidence Slider (>= 0.50)     |                                    |                               |
|                                    | [2.3] Status & Zoom Ratio Footer   | [3.3] Export Actions Toolbar  |
| [1.3] Action Controls              |                                    |  - [Sao chép] [Tải TXT/MD/JSON|
|  - [ Nút Chạy OCR / Trích xuất ]   |                                    |                               |
|  - [ Nút Xóa / Reset (Abort Req) ] |                                    |                               |
|                                    |                                    |                               |
| [1.4] PDF Pages Thumbnail List     |                                    |                               |
|  - Danh sách thumbnail các trang   |                                    |                               |
+------------------------------------+------------------------------------+-------------------------------+
```

### 3.1. Cột 1: Upload, Cấu hình & Quản lý Tài liệu (Left Column — 25% Width / Min 280px)
- **Khu vực Tải tệp (Compact Dropzone)**:
  - Thiết kế nét đứt tinh tế, kích thước vừa phải, nhận drag-and-drop và click để chọn file.
  - Hỗ trợ định dạng: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, `.bmp` (giới hạn tối đa 20MB).
  - **Validation kích thước ảnh an toàn**:
    ```javascript
    // app.js — Kiểm tra kích thước điểm ảnh trước khi upload
    async function validateImageDimensions(file) {
        if (file.type.startsWith('image/')) {
            const bitmap = await createImageBitmap(file);
            if (bitmap.width > 8000 || bitmap.height > 8000) {
                showToast('warning', `Ảnh kích thước lớn (${bitmap.width}x${bitmap.height}px), có thể mất nhiều thời gian xử lý.`);
            }
            bitmap.close();
        }
    }
    ```
  - Khi đã có file: Hiển thị thẻ tóm tắt (Icon định dạng, Tên tệp, Kích thước, Số trang) kèm nút đổi tệp nhanh.
- **Tùy chọn xử lý (Processing Options)**:
  - Lựa chọn Endpoint / Chế độ phân tích:
    - `OCR Only` (Nhận diện dòng chữ - `/api/v1/ocr`)
    - `Document Extraction Pipeline` (Phân tích Layout + Bảng Markdown + OCR Tiếng Việt - `/api/v1/document/extract`)
  - **Tùy chọn mở rộng khi chọn Document Pipeline**:
    - Độ phân giải render PDF (`resolution`): Radio button `72 DPI (Nhanh)` / `150 DPI (Tiêu chuẩn)` / `300 DPI (Sắc nét)`. *(Lưu ý: Backend enforce ràng buộc `72 ≤ resolution ≤ 300`).*
    - Trích xuất bảng (`extract_tables`): Checkbox bật/tắt (Mặc định: `true`).
  - **Slider lọc độ tin cậy hiển thị BBox (Confidence Threshold)**:
    - Dải giá trị: `0.50` - `1.00` (Mặc định `0.50`, bước nhảy `0.05`).
    - Ghi chú Tooltip: *"Ngưỡng lọc tối thiểu phía máy chủ là 0.50 (`settings.DROP_SCORE`). Slider giúp lọc sâu hơn trên giao diện."*
- **Nút hành động chính & Quản lý Hủy Request (Action CTA & Abort)**:
  - Nút **"Nhận dạng OCR / Trích xuất"** (Primary Indigo Button) có hiệu ứng loading spinner khi đang xử lý.
  - Nút **"Xóa / Làm mới"** (Outline Button) gọi `abortCurrentRequest()` để hủy ngay lập tức request HTTP đang chạy ngầm (nếu có), sau đó dọn dẹp bộ nhớ và reset state.
  - Nút **"Thử lại" (Retry Action Guard)**: Khi gặp lỗi 500 (`INFERENCE_ERROR` / `INTERNAL_SERVER_ERROR`), nút Retry sẽ gọi hàm `handleRetry()` để kiểm tra sức khỏe backend (`checkHealth()`) trước khi gửi lại request, tránh vòng lặp lỗi lặp đi lặp lại.
- **Lưu ý Cài đặt Môi trường (Deployment Note cho Document Pipeline)**:
  > **Quan trọng:** Endpoint `/api/v1/document/extract` yêu cầu gói phụ thuộc tùy chọn `pdfplumber` (`[pdf]`). Nếu chạy môi trường local, cần đảm bảo đã cài đặt `pip install -e ".[cpu,pdf]"` (môi trường Dockerfile đã cài sẵn). Nếu backend thiếu gói này, request sẽ trả về `500 INTERNAL_SERVER_ERROR`.
- **Ma trận xử lý lỗi API Chuẩn hóa (Error Response Matrix — Khớp Backend Exceptions)**:

| Mã HTTP | `error_code` Thực tế Backend | Tình huống phát sinh | Phản hồi giao diện người dùng (UI Response) |
| :--- | :--- | :--- | :--- |
| **400** | `INVALID_VALUE` | File rỗng, `cv2.imdecode` thất bại, tham số sai | Toast vàng: *"Dữ liệu không hợp lệ: {detail}"* |
| **400** | `INVALID_FILE_FORMAT` | Định dạng file không được hỗ trợ bởi service | Toast đỏ: *"Định dạng tệp không được hỗ trợ."* |
| **400** | `BAD_REQUEST` | Tệp rỗng hoặc không có tệp đính kèm | Toast đỏ: *"Tệp tải lên không hợp lệ hoặc rỗng."* |
| **413** | `PAYLOAD_TOO_LARGE` | File upload vượt quá giới hạn 20MB (Client check) | Toast đỏ: *"File vượt quá kích thước cho phép (tối đa 20MB)."* |
| **422** | `VALIDATION_ERROR` | Schema tham số request không khớp Pydantic | Toast vàng: *"Dữ liệu yêu cầu không hợp lệ."* + Tự động switch sang Tab 3 (JSON) hiển thị chi tiết. |
| **500** | `MODEL_NOT_FOUND` | Máy chủ thiếu model weights ONNX | Toast đỏ: *"Lỗi máy chủ: Không tìm thấy model weights."* |
| **500** | `INFERENCE_ERROR` | Model crash trong quá trình suy luận ONNX | Toast đỏ: *"Lỗi suy luận mô hình."* + Nút *"Thử lại"* (Retry). |
| **500** | `FILE_NOT_FOUND` | Máy chủ không tìm thấy tài nguyên hệ thống | Toast đỏ: *"Lỗi máy chủ: Không tìm thấy tài nguyên."* |
| **500** | `INTERNAL_SERVER_ERROR`| Backend gặp sự cố không xác định / thiếu `[pdf]` | Toast đỏ: *"Máy chủ gặp sự cố khi xử lý."* + Nút *"Thử lại"* (Retry). |
| **Timeout (> 30s)** | `TIMEOUT` | Xử lý tài liệu lớn hoặc khởi động model lần đầu | Hiển thị Banner Loading: *"Đang khởi tạo mô hình AI / Xử lý tài liệu lớn, vui lòng đợi..."* |
| **Network Offline** | `DISCONNECT` | Mất kết nối tới Backend FastAPI | Badge trạng thái Topbar chuyển đỏ: *"Mất kết nối API"* + Toast cảnh báo. |

---

### 3.2. Cột 2: Trình xem trước & Trực quan hóa Bounding Box (Center Column — 45% Width / Min 420px)
- **Thanh công cụ Viewer (Viewer Toolbar)**:
  - Phóng to (`+`), Thu nhỏ (`-`), Vừa khung (`Fit`), Kích thước thực (`100%`).
  - Nút gạt bật/tắt hiển thị Bounding Box (`Toggle BBox`).
  - Thanh chuyển trang nhanh (Dành cho PDF: `Trang X / Y`).
- **Khung hiển thị hình ảnh (Interactive Viewport)**:
  - Vùng chứa hỗ trợ cuộn và kéo rê di chuyển (Pan) khi zoom lớn.
  - Lớp phủ BBox hỗ trợ cả SVG Layer hoặc Canvas Overlay, chuẩn hóa mọi loại bbox về 4-point polygon trước khi vẽ.
- **Đồng bộ Tỷ lệ Render PDF giữa PDF.js và Backend (DPI Synchronization)**:
  > **Quy chuẩn kỹ thuật bắt buộc:**  
  > 1. Khi ở chế độ `/api/v1/document/extract`, backend render PDF qua `pdfplumber` với `resolution` DPI (`72`, `150`, `300`).  
  > 2. `pdf-loader.js` **tính toán tỷ lệ scale chính xác tuyệt đối theo công thức động**:  
  >    ```javascript
  >    const PDF_POINTS_PER_INCH = 72;
  >    function dpiToScale(dpi) {
  >        return dpi / PDF_POINTS_PER_INCH; // 72 -> 1.0; 150 -> 2.083333...; 300 -> 4.166666...
  >    }
  >    const scale = dpiToScale(AppState.config.resolution);
  >    ```  
  > 3. Tỷ lệ này đảm bảo `naturalWidth` và `naturalHeight` của Canvas ở client khớp chính xác với kích thước ảnh mà backend đã dùng để suy luận OCR/Layout, triệt tiêu hoàn toàn hiện tượng lệch BBox.
- **Yêu cầu Bắt buộc khi Gửi Blob lên OCR Endpoint**:
  > Khi trích xuất ảnh từng trang từ Canvas để gửi lên `/api/v1/ocr`, **phải luôn cung cấp tham số `filename`** trong `FormData.append`:
  > ```javascript
  > formData.append('file', blob, `page_${pageNum}.png`); // Bắt buộc có filename để FastAPI không báo lỗi 400
  > ```
- **Chuẩn hóa BBox & Hệ tọa độ Pixel Tuyệt đối**:
  > 1. **Chuẩn hóa BBox (Normalization)**:  
  >    - Nếu đầu vào là 4-point polygon `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]` (từ `OCRLineResult`): Giữ nguyên.  
  >    - Nếu đầu vào là flat array 4-float `[x1, y1, x2, y2]` (từ `LayoutRegionResult` / `TableComponent`): Tự động chuyển đổi thành `[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]`.  
  > 2. **Tỷ lệ scale động**:  
  >    $$\text{scaleX} = \frac{\text{displayWidth}}{\text{naturalWidth}}, \quad \text{scaleY} = \frac{\text{displayHeight}}{\text{naturalHeight}}$$  
  >    Tọa độ màn hình: $\text{screenX} = x_{\text{orig}} \times \text{scaleX}, \quad \text{screenY} = y_{\text{orig}} \times \text{scaleY}$.  
  > 3. Xử lý chuẩn hóa xoay ảnh (EXIF Orientation) nếu hình ảnh chụp từ điện thoại bị đảo chiều.
- **Tương tác trực quan 2 chiều (Bidirectional Interactions)**:
  - Rê chuột vào BBox trên ảnh: Đổi màu viền (Indigo $\rightarrow$ Emerald), hiện Tooltip (Text & Confidence Score), đồng thời phát sự kiện `line:hover` để tự động cuộn và làm nổi bật dòng văn bản ở Cột 3.

---

### 3.3. Cột 3: Kết quả Văn bản & Kiểm tra Chi tiết (Right Column — 30% Width / Min 320px)
- **Thẻ thống kê hiệu năng (Execution Metrics Card)**:
  - Thời gian xử lý backend (`elapsed_ms`).
  - Tổng số dòng văn bản trích xuất (`total_lines`).
  - **Điểm tin cậy trung bình (`avgConfidence`)**: Do schema `OCRResponse` không trả trực tiếp `avg_confidence`, Frontend **tự động tính toán trên client**:  
    $$\text{avgConfidence} = \frac{\sum_{i=1}^{N} \text{score}_i}{N} \quad (\text{với } N = \text{total\_lines} > 0)$$
- **Vùng hiển thị nội dung kết quả (Accessible Result Container)**:
  - Khung chứa có thuộc tính `aria-live="polite"` và `aria-atomic="false"` để người dùng sử dụng trình đọc màn hình (Screen Reader) được thông báo tức thì khi có kết quả OCR mới mà không bị gián đoạn.
- **Hệ thống Tab đa góc nhìn (Multi-view Tabs)**:
  - **Tab 1: Raw Text / Markdown View**:
    - Khi ở chế độ `/api/v1/ocr`: Textarea hiển thị toàn bộ văn bản ghép từ `lines[].text`.
    - Khi ở chế độ `/api/v1/document/extract`: Hiển thị `full_markdown` (Markdown hợp nhất hoàn chỉnh có tiêu đề, đoạn văn và bảng biểu).
    - **Xử lý Fallback khi Markdown rỗng**: Nếu `full_markdown` rỗng (ví dụ: tài liệu chỉ chứa bảng biểu mà không có văn bản đoạn), hiển thị thông báo gợi ý: *"Tài liệu không có đoạn văn bản thuần. Xem dữ liệu bảng biểu chi tiết tại Tab 3 (JSON)."*
  - **Tab 2: Line Details (Từng dòng)**: Danh sách cuộn từng dòng chữ với badge điểm tin cậy (Xanh lá $\ge 90\%$, Vàng $70-89\%$, Đỏ $< 70\%$). Click/Hover vào dòng sẽ phát sự kiện `bbox:hover` để highlight và căn giữa BBox tương ứng ở Cột 2.
    - **Lưu ý Chính xác về Data Integrity**: Trong Document Pipeline, `text_lines[]` chứa toàn bộ kết quả OCR thô. Bộ lọc `drop_garbage` của backend chỉ loại bỏ các số trang đơn giản (regex `^\d{1,3}(/\d{1,3})?$`) ở vùng 8% trên/dưới trang. Các vùng layout loại `"reference"` (danh mục tài liệu tham khảo) **vẫn được giữ nguyên** và hiển thị đầy đủ trên cả Tab 2 và Markdown.
  - **Tab 3: Raw JSON**: Xem toàn bộ payload JSON trả về từ API (`OCRResponse` hoặc `DocumentExtractionResponse`) có định dạng thụt lề chuẩn.
- **Thanh thao tác dữ liệu (Export Toolbar)**:
  - Nút **"Sao chép văn bản / Markdown"** (Copy to Clipboard kèm Toast phản hồi).
  - Nút **"Tải về .TXT / .MD"** (Lưu tệp plain text hoặc markdown về máy).
  - Nút **"Tải về .JSON"** (Lưu tệp JSON kết quả chi tiết).

---

### 3.4. Chiến lược Đáp ứng Giao diện (Responsive Strategy & Breakpoints)

Để đảm bảo trải nghiệm không bị vỡ giao diện trên các kích thước màn hình khác nhau, hệ thống áp dụng chiến lược 3 tầng:

```
                  +-------------------------------------------------------------+
                  |                     CHIẾN LƯỢC RESPONSIVE                   |
                  +-------------------------------------------------------------+
                  |                                                             |
Màn hình Lớn      | [ >= 1280px (Desktop / Màn hình ngang) ]                    |
                  | -> 3 Cột song song đầy đủ (CSS Grid: 25% | 45% | 30%)       |
                  |                                                             |
Màn hình Trung    | [ 768px - 1279px (Laptop nhỏ / Tablet ngang) ]               |
                  | -> 2 Cột hiển thị: Cột 2 (Preview 55%) + Cột 3 (Results 45%) |
                  | -> Cột 1 (Upload/Config) thu vào Offcanvas Drawer (Sidebar) |
                  |                                                             |
Màn hình Nhỏ      | [ < 768px (Mobile / Tablet dọc) ]                           |
                  | -> Single-Column với Tab Navigation (1: Upload | 2: Preview | 3: Result) |
                  | -> Hiển thị Thông báo đề xuất màn hình >= 1280px             |
                  +-------------------------------------------------------------+
```

1. **Màn hình Lớn ($\ge 1280\text{px}$ — Full Desktop View)**:
   - Hiển thị đầy đủ 3 Cột song song cố định chiều cao bằng `100vh - Header`, mỗi cột có thanh cuộn độc lập (`overflow-y: auto`).
2. **Màn hình Trung bình ($768\text{px} - 1279\text{px}$ — Tablet / Small Laptop View)**:
   - Cột 1 (Upload & Cấu hình) được thu gọn vào **Offcanvas Sidebar (Drawer)**, mở ra khi click nút menu trên Topbar hoặc khi cần chọn tệp mới.
   - Cột 2 (Document Preview - 55%) và Cột 3 (OCR Results - 45%) chia sẻ không gian làm việc chính.
3. **Màn hình Nhỏ ($< 768\text{px}$ — Mobile View)**:
   - Giao diện chuyển sang chế độ 1 cột duy nhất với **Tab Bar điều hướng dưới chân (Bottom Navigation)**: `[Tải tệp & Cấu hình]` $\leftrightarrow$ `[Xem tài liệu]` $\leftrightarrow$ `[Kết quả OCR]`.
   - Hiển thị một Banner thông báo nhẹ: *"Khuyến nghị sử dụng màn hình máy tính ($\ge 1280\text{px}$) để có trải nghiệm đối chiếu Bounding Box tốt nhất."*

---

## 4. Hệ thống Thiết kế & Ngăn xếp Công nghệ (Design System & Tech Stack)

### 4.1. Lựa chọn Công nghệ & Thư viện
1. **Bố cục Layout bằng CSS Grid kết hợp Bootstrap 5.3 Utilities**:
   - Sử dụng CSS Grid cho vùng làm việc chính:  
     `grid-template-columns: minmax(280px, 25%) minmax(420px, 45%) minmax(320px, 30%);`
   - Sử dụng Bootstrap 5.3 (CSS & Bundle JS qua CDN) cho Buttons, Badges, Tabs, Offcanvas, Modals, Tooltips và Toasts.
2. **Bootstrap Icons (CDN)**:
   - Bộ icon vector nhẹ, đồng bộ cho toàn bộ công cụ (Upload, Zoom, Fit, Copy, Download, Refresh...).
3. **Custom CSS Design Tokens (Tuân thủ `ui/design.md`)**:
   - Palette màu chuyên nghiệp (Slate & Indigo):
     - Surface: Background `#f8fafc`, Surface Card `#ffffff`, Border `#e2e8f0`.
     - Brand: Primary `#4f46e5`, Primary Hover `#4338ca`, Primary Light `#e0e7ff`.
     - Status: Emerald `#10b981` (High Conf / Ready), Amber `#f59e0b` (Mid Conf / Warming up), Rose `#ef4444` (Low Conf / Error).
   - Typography: Font Google `Plus Jakarta Sans` / `Inter` cho nội dung văn bản, `JetBrains Mono` cho JSON/Code.
4. **PDF.js v3.11.174 (CDN - Ghim phiên bản cố định)**:
   - Ghim đúng version CDN và cấu hình bắt buộc worker để tránh lỗi CORS runtime:
     ```javascript
     const PDFJS_VERSION = '3.11.174';
     pdfjsLib.GlobalWorkerOptions.workerSrc = 
       `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.worker.min.js`;
     ```
5. **Modular JavaScript (ES6 Vanilla — Native Browser Modules)**:
   - Không cần bước build (Webpack/Vite/Babel); tận dụng module ES6 Controller/Service sạch sẽ, nhẹ và dễ bảo trì.

---

## 5. Kiến trúc Module JavaScript & Quản lý Trạng thái

Cấu trúc thư mục mã nguồn được phân định trách nhiệm rõ ràng (Separation of Concerns):

```
ui/
├── index.html            # Trang giao diện chính (HTML5 + Bootstrap 5.3 + CSS Grid)
├── style.css             # Design Tokens, CSS Grid 3 cột, BBox overlay, Responsive styles
├── js/
│   ├── api.js            # Giao tiếp Backend REST API (/api/v1/ocr, /api/v1/document/extract, Health check, AbortController)
│   ├── state.js          # Quản lý State tập trung (AppState, Computed state, Page Eviction & Event Bus)
│   ├── pdf-loader.js     # Trích xuất, render thumbnail PDF, đồng bộ DPI scale, giải phóng Object URL
│   ├── bbox-renderer.js  # Chuẩn hóa BBox, tính toán scale pixel, vẽ BBox & tương tác hover
│   └── app.js            # Controller chính, khởi tạo ứng dụng, lắng nghe Event Bus & DOM
└── design.md             # Tài liệu chuẩn thiết kế gốc
```

### 5.1. Mô hình Trạng thái Ứng dụng (AppState Model) & Schema Mapping

```javascript
const AppState = {
    // Trạng thái tệp tải lên
    file: {
        raw: null,             // File object gốc
        name: '',
        size: 0,
        type: '',              // 'image' hoặc 'pdf'
        dataUrl: null,
    },
    // Trạng thái PDF & Quản lý Cache từng trang
    pdf: {
        doc: null,
        totalPages: 0,
        currentPage: 1,
        // pagesData: [{ pageNum, dataUrl, width, height, ocrResult, cacheKey }]
        pagesData: [],
    },
    // Trạng thái Trình xem (Viewer)
    viewer: {
        zoomLevel: 1.0,
        showBBox: true,
        confidenceThreshold: 0.5, // Mặc định 0.50 khớp với settings.DROP_SCORE của backend
        activeLineIndex: null,    // Index dòng đang được highlight
    },
    // Kết quả hiện tại (Tự động đồng bộ filteredLines)
    activeResult: {
        rawResponse: null,     // Toàn bộ response object từ API
        lines: [],             // Danh sách OCRLineResult hiển thị
        filteredLines: [],     // Computed: lines.filter(l => l.score >= viewer.confidenceThreshold)
        fullMarkdown: '',      // Markdown hợp nhất (khi dùng Document Extraction)
        totalLines: 0,
        elapsedMs: 0,
        avgConfidence: 0,      // Computed trên client: sum(scores) / lines.length
    },
    // Cấu hình kết nối & Endpoint
    config: {
        endpoint: '/api/v1/ocr', // '/api/v1/ocr' hoặc '/api/v1/document/extract'
        extractTables: true,     // Dùng cho Document Extraction
        resolution: 150,         // Dùng cho Document Extraction (72, 150, 300 DPI)
        apiBaseUrl: window.location.origin,
    },
    serverStatus: {
        connected: false,
        modelsReady: false,
    },
    isLoading: false,
};
```

**Bảng Mapping Response Schema Backend $\rightarrow$ Frontend UI:**

| Chế độ Endpoint | Schema Trả về | Nguồn Dòng BBox (`lines`) | Nguồn Text chính Tab 1 | Tab 3 JSON |
| :--- | :--- | :--- | :--- | :--- |
| **OCR Only** (`/api/v1/ocr`) | `OCRResponse` | `response.lines[]` | Nối chuỗi `lines[].text` | Toàn bộ `OCRResponse` |
| **Document Pipeline** (`/api/v1/document/extract`) | `DocumentExtractionResponse` | `response.pages[pageNum - 1].text_lines[]` *(chứa raw OCR)* | `response.full_markdown` *(kết quả đã fuse layout)* | Toàn bộ `DocumentExtractionResponse` |

> **Chiến lược Quản lý Bộ nhớ & Thu hồi Cache (Memory & Eviction Rules):**
> 1. **Page Eviction cho `dataUrl` Base64**: Đối với PDF nhiều trang, chỉ lưu giữ chuỗi `dataUrl` trong RAM cho cửa sổ trang hoạt động `[currentPage - 2, currentPage + 2]`. Các trang ở xa sẽ gán `p.dataUrl = null` (chỉ giữ `cacheKey` và `ocrResult`), khi người dùng cuộn tới sẽ render lại theo yêu cầu (on-demand) từ PDF.js để tránh tràn bộ nhớ JS Heap.
> 2. **Hủy Cache khi đổi cấu hình**: Khi `file.raw`, `config.endpoint`, `config.resolution` hoặc `config.extractTables` thay đổi, toàn bộ cache trang trong `pagesData[]` sẽ bị hủy và reset sạch.
> 3. Khóa định danh cache cho từng trang (Cache Key):  
>    `cacheKey = `${file.name}-${file.size}-${config.endpoint}-r${config.resolution}-t${config.extractTables}-p${pageNum}``

---

### 5.2. Mô hình Event Bus Tập trung (Event Bus Pattern)

Để đảm bảo các module giao tiếp lỏng lẻo (loosely coupled), `state.js` cung cấp cơ chế Event Bus pub/sub an toàn:

```javascript
// state.js — Event Bus tối giản và an toàn
export const EventBus = {
    listeners: {},
    on(event, callback) {
        (this.listeners[event] ??= []).push(callback);
    },
    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    },
    emit(event, payload) {
        this.listeners[event]?.forEach(callback => {
            try {
                callback(payload);
            } catch (err) {
                console.error(`[EventBus] Error in event '${event}':`, err);
            }
        });
    }
};
```

**Danh mục Sự kiện Chuẩn (Standard Event Catalog):**
- `'file:loaded'`: Phát khi tệp mới được tải lên và validate thành công `({ file, type })`. *(⚠️ Bắt buộc: Handler của sự kiện này phải gọi `abortCurrentRequest()` trước khi cập nhật `AppState.file` và phát `cache:clear`)*.
- `'ocr:start'`: Phát khi bắt đầu gửi request OCR lên máy chủ.
- `'ocr:complete'`: Phát khi nhận dữ liệu kết quả từ backend thành công `({ result, metrics })`.
- `'ocr:error'`: Phát khi gặp lỗi mạng hoặc API trả về mã lỗi `({ statusCode, errorCode, detail })`.
- `'line:hover'`: Phát khi người dùng rê chuột vào dòng văn bản ở Cột 3 `({ lineIndex })`.
- `'bbox:hover'`: Phát khi người dùng rê chuột vào BBox trên ảnh ở Cột 2 `({ lineIndex })`.
- `'threshold:change'`: Phát khi người dùng thay đổi slider điểm tin cậy `({ threshold })`.
- `'page:change'`: Phát khi người dùng chuyển trang tài liệu PDF `({ pageNum })`.
- `'server:status'`: Phát khi trạng thái kết nối backend/model readiness thay đổi `({ connected, modelsReady })`.
- `'cache:clear'`: Phát khi toàn bộ cache trang cần được giải phóng và làm sạch.

---

## 6. Lộ trình Triển khai Chi tiết (Step-by-Step Implementation Roadmap)

Lộ trình thực hiện gồm 4 giai đoạn rõ ràng:

### Giai đoạn 1: Thiết lập Khung Giao diện & Layout CSS Grid
- [ ] **Bước 1.1**: Tái cấu trúc `ui/index.html`. Nhúng Bootstrap 5.3 CDN, Bootstrap Icons CDN, Google Fonts (`Inter`, `Plus Jakarta Sans`, `JetBrains Mono`).
- [ ] **Bước 1.2**: Xây dựng Topbar:
  - Logo và Tiêu đề dự án "Vietnamese OCR Demo".
  - **Badge trạng thái thông minh (Health & Readiness Badge)**:
    - Xanh lá: `Connected & Ready` (`status === 'ok'` & `models_ready === true`).
    - Vàng: `Models Initializing...` (`status === 'ok'` & `models_ready === false`).
    - Đỏ: `API Disconnected` (Không kết nối được server).
  - Nút mở Offcanvas menu cho màn hình nhỏ, và liên kết API Docs (`/docs`).
- [ ] **Bước 1.3**: Thiết lập khung CSS Grid 3 cột chiếm toàn bộ chiều cao màn hình (`height: calc(100vh - 56px)`):
  - Khung làm việc chính: `.app-layout-grid` với tỷ lệ `25% / 45% / 30%`.
  - Cột 1: `<aside class="column-upload d-flex flex-column ...">`
  - Cột 2: `<section class="column-preview d-flex flex-column ...">`
  - Cột 3: `<section class="column-results d-flex flex-column ...">`
  - Tích hợp Offcanvas Sidebar cho Cột 1 tại breakpoint `$md` ($< 1280\text{px}$).
- [ ] **Bước 1.4**: Cập nhật `ui/style.css` bổ sung CSS Design Tokens, tùy biến thanh cuộn, style cho BBox overlay, thẻ metrics, viewport zoom/pan và media queries responsive.

### Giai đoạn 2: Phát triển Chi tiết Giao diện Từng Cột
- [ ] **Bước 2.1 (Cột 1 - Upload & Config)**:
  - Vùng Drag-and-Drop nhỏ gọn với icon tải lên và text hướng dẫn, tích hợp hàm `validateImageDimensions()`.
  - Thẻ thông tin tệp (File metadata badge) kèm icon định dạng và kích thước tệp.
  - Panel cài đặt tham số:
    - Selector chế độ: `OCR Only (/api/v1/ocr)` vs `Document Extraction (/api/v1/document/extract)`.
    - Group tùy chọn Document: Radio DPI (`72`, `150`, `300`) và Checkbox `extract_tables`.
    - Slider lọc ngưỡng tin cậy (`0.50` - `1.00`, default `0.50`).
  - Nút "Chạy OCR / Trích xuất" với hiệu ứng Spinner và trạng thái disabled khi đang xử lý.
  - Danh sách thumbnail trang PDF với khả năng bấm chọn trang nhanh.
- [ ] **Bước 2.2 (Cột 2 - Viewer & Visualizer)**:
  - Thanh công cụ Viewport: Nút Zoom In, Zoom Out, Reset 100%, Fit Width, Toggle BBox.
  - Vùng chứa ảnh (`viewport-container`) có khả năng cuộn và kéo rê di chuyển hình ảnh (Pan).
  - Khung Canvas/SVG Overlay vẽ bounding boxes dựa trên tọa độ pixel tuyệt đối đã chuẩn hóa.
- [ ] **Bước 2.3 (Cột 3 - Results & Actions)**:
  - Thẻ tóm tắt thông số: Thời gian thực thi (`elapsed_ms`), Tổng số dòng, Điểm tin cậy TB (`avgConfidence` tự tính).
  - Vùng chứa kết quả gắn `aria-live="polite"` cho khả năng tiếp cận (Accessibility).
  - 3 Tabs chuyển đổi:
    - Tab 1: Raw Text / Markdown View (hiển thị `full_markdown` khi chọn Document Pipeline; có fallback khi rỗng).
    - Tab 2: Danh sách Cards/Items cho từng dòng văn bản (kèm số thứ tự và badge score; ghi chú chính xác về raw OCR).
    - Tab 3: Khung xem cú pháp JSON có định dạng rõ ràng.
  - Footer Action Bar: Nút Copy nhanh, Nút tải xuống `.txt/.md`, Nút tải xuống `.json`.

### Giai đoạn 3: Module hóa & Hoàn thiện Mã nguồn JavaScript
- [ ] **Bước 3.1 (`api.js`)**:
  - Xây dựng hàm kiểm tra sức khỏe và cơ chế **Smart Health Polling**:
    ```javascript
    let _healthPollTimer = null;
    export async function startHealthPolling() {
        const result = await checkHealth();
        EventBus.emit('server:status', result);
        if (!result.connected || !result.modelsReady) {
            // Chưa sẵn sàng hoặc đang nạp model -> poll lại sau 5s
            _healthPollTimer = setTimeout(startHealthPolling, 5000);
        }
    }
    export function stopHealthPolling() {
        if (_healthPollTimer) {
            clearTimeout(_healthPollTimer);
            _healthPollTimer = null;
        }
    }
    ```
  - **Quản lý Hủy Request (`AbortController`)**:
    ```javascript
    let _activeController = null;
    export function abortCurrentRequest() {
        if (_activeController) {
            _activeController.abort();
            _activeController = null;
        }
    }
    ```
  - Xây dựng hàm `sendOcrRequest(fileOrBlob, filename = 'image.png')`:
    ```javascript
    abortCurrentRequest();
    _activeController = new AbortController();
    const formData = new FormData();
    formData.append('file', fileOrBlob, filename); // Bắt buộc có filename
    return fetch(`${apiBaseUrl}/api/v1/ocr`, {
        method: 'POST', body: formData, signal: _activeController.signal
    });
    ```
  - Xây dựng hàm `sendDocumentRequest(file, extractTables, resolution)` với **URL Query Params**:
    ```javascript
    abortCurrentRequest();
    _activeController = new AbortController();
    const url = new URL(`${apiBaseUrl}/api/v1/document/extract`);
    url.searchParams.set('extract_tables', extractTables);
    url.searchParams.set('resolution', resolution);
    const formData = new FormData();
    formData.append('file', file, file.name || 'document.pdf');
    return fetch(url.toString(), {
        method: 'POST', body: formData, signal: _activeController.signal
    });
    ```
  - Tích hợp **Error Response Matrix** chi tiết xử lý theo cả HTTP status và chuỗi `error_code` thực tế (`INVALID_VALUE`, `INVALID_FILE_FORMAT`, `MODEL_NOT_FOUND`, `INFERENCE_ERROR`, `INTERNAL_SERVER_ERROR`).
  - Xử lý làm sạch (sanitize) chuỗi trước khi gán vào DOM để phòng ngừa XSS.
- [ ] **Bước 3.2 (`pdf-loader.js`)**:
  - Cấu hình PDF.js worker cố định theo phiên bản CDN (`3.11.174`).
  - **Đồng bộ hóa DPI Render Động:** Áp dụng scale factor tương ứng với resolution (`scale = resolution / 72`).
  - Trích xuất trang PDF sang Canvas, xuất ảnh blob tạo thumbnail (gọi `URL.revokeObjectURL()` dọn dẹp bộ nhớ).
  - Triển khai hàm `evictDistantPages(currentPage)` để giải phóng các chuỗi `dataUrl` Base64 ngoài vùng hiển thị.
  - Quản lý bộ nhớ đệm kết quả OCR theo từng trang (`cacheKey`).
- [ ] **Bước 3.3 (`bbox-renderer.js`)**:
  - Triển khai hàm chuẩn hóa BBox hỗ trợ cả polygon và flat rect:
    ```javascript
    function normalizeBbox(bbox) {
        if (Array.isArray(bbox[0])) return bbox; // 4-point polygon (OCR)
        const [x1, y1, x2, y2] = bbox;          // 4-float rect (Layout/Table)
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]];
    }
    ```
  - Tính toán tỷ lệ tọa độ scale giữa kích thước thực (`naturalWidth/Height`) và kích thước hiển thị (`displayWidth/Height`).
  - Vẽ BBox dạng polygon 4 điểm chính xác trên Canvas hoặc SVG.
  - Lọc danh sách BBox theo `AppState.activeResult.filteredLines` phản ứng nhanh theo Slider.
  - Xử lý đồng bộ 2 chiều qua Event Bus (`line:hover` $\leftrightarrow$ `bbox:hover`).
- [ ] **Bước 3.4 (`state.js` & `app.js`)**:
  - Triển khai Event Bus và quản lý `AppState`.
  - Tự động cập nhật `filteredLines` và tính toán `avgConfidence` khi có kết quả mới hoặc khi thay đổi `confidenceThreshold`.
  - Lắng nghe sự kiện `file:loaded` gọi tường minh `abortCurrentRequest()` trước khi update state:
    ```javascript
    EventBus.on('file:loaded', ({ file, type }) => {
        abortCurrentRequest(); // Bắt buộc gọi đầu tiên để hủy request cũ
        EventBus.emit('cache:clear');
        AppState.file = { raw: file, name: file.name, size: file.size, type };
    });
    ```
  - Triển khai hàm `handleRetry()` kiểm tra sức khỏe backend trước khi gửi lại:
    ```javascript
    async function handleRetry() {
        const health = await checkHealth();
        if (!health.connected) {
            showToast('error', 'Backend chưa kết nối được. Vui lòng thử lại sau.');
            return;
        }
        if (!health.modelsReady) {
            showToast('warning', 'Mô hình AI đang khởi tạo, vui lòng đợi giây lát...');
            return;
        }
        submitOcrRequest();
    }
    ```
  - Kết nối toàn bộ sự kiện DOM, quản lý vòng đời ứng dụng và hiển thị Toasts thông báo.

### Giai đoạn 4: Kiểm thử, Tối ưu & Đánh giá Tiêu chuẩn
- [ ] **Bước 4.1**: Kiểm thử trực tiếp với các định dạng ảnh mẫu (ảnh chụp hóa đơn, scan tài liệu, chữ in, chữ mờ, các cỡ phân giải khác nhau).
- [ ] **Bước 4.2**: Kiểm thử tài liệu PDF nhiều trang (1 đến 20+ trang), kiểm tra tính đồng bộ DPI của BBox ở các mức resolution 72/150/300 DPI, kiểm tra cơ chế Eviction bộ nhớ RAM khi chuyển qua lại nhiều trang.
- [ ] **Bước 4.3**: Kiểm tra tính tương thích Responsive trên các độ phân giải màn hình (Desktop $\ge 1280\text{px}$, Laptop $1024\text{px}$, Tablet $768\text{px}$, Mobile $< 768\text{px}$).
- [ ] **Bước 4.4**: Rà soát tiêu chuẩn Accessibility (WCAG 2.2 AA) theo `ui/design.md`: Hỗ trợ điều hướng bàn phím, độ tương phản màu sắc đạt chuẩn, thẻ ARIA đầy đủ.

---

## 7. Tiêu chí Nghiệm thu & Checklist Kiểm tra Chất lượng (QA Checklist)

| STT | Tiêu chí nghiệm thu | Phương pháp kiểm tra | Kết quả mong đợi |
| :--- | :--- | :--- | :--- |
| 1 | **Bố cục 3 Cột & Responsive** | Mở trên Desktop ($\ge 1280\text{px}$), Tablet ($768-1279\text{px}$) và Mobile ($<768\text{px}$) | 3 Cột hiển thị song song ở Desktop; Offcanvas ở Tablet; Tabbed View ở Mobile; không vỡ layout. |
| 2 | **Kéo thả & Xem trước Tệp** | Kéo file ảnh/PDF bất kỳ vào Dropzone | Nhận diện đúng file, render preview ngay lập tức ở Cột 2 trong $< 200\text{ms}$; cảnh báo nếu ảnh $> 8000\text{px}$. |
| 3 | **Kết nối Backend & Health Status** | Quan sát Badge Topbar khi backend khởi động | Hiển thị Vàng khi model đang nạp (`models_ready: false`), chuyển Xanh lá khi sẵn sàng (`models_ready: true`). |
| 4 | **Gọi API OCR & Document Extraction** | Gửi request `/api/v1/ocr` và `/api/v1/document/extract` kèm Query Params | Gọi đúng endpoint, truyền đúng `filename` trong FormData, nhận diện thành công. |
| 5 | **Độ chính xác BBox & Đồng bộ DPI** | Kiểm tra BBox với PDF ở 72, 150, 300 DPI và với layout region (4-float rect) | Khung viền ôm sát đối tượng ở mọi DPI; hàm `normalizeBbox()` hoạt động chính xác không gây lệch tọa độ. |
| 6 | **Hủy Request Đang Chạy (Abort)** | Nhấn "Xóa / Làm mới" hoặc chọn tệp mới khi đang gửi request xử lý lớn | Request HTTP bị hủy ngay lập tức qua `AbortController`, không ghi đè dữ liệu cũ lên UI. |
| 7 | **Đồng bộ 2 chiều (Event Bus)** | Rê chuột vào BBox trên ảnh hoặc dòng text ở Cột 3 | Cả 2 phần tử cùng sáng viền và tự động cuộn tới vị trí tương ứng tức thì. |
| 8 | **Chức năng Xuất dữ liệu** | Bấm nút Sao chép & Tải tệp TXT/MD/JSON | Copy đúng nội dung Unicode Tiếng Việt vào Clipboard; tải về file `.txt`, `.md` và `.json` nguyên vẹn. |
| 9 | **Hỗ trợ PDF & Quản lý Bộ nhớ** | Tải file PDF 20+ trang, chuyển trang liên tục | Render thumbnail mượt mà; giải phóng `revokeObjectURL()` và evict các trang ở xa, không rò rỉ RAM. |
| 10 | **Bảo mật File & Xử lý Lỗi chuẩn Backend** | Upload file hỏng hoặc gửi request sai | Backend trả về đúng `error_code` (`INVALID_VALUE`, `INVALID_FILE_FORMAT`...); UI hiển thị đúng Toast theo ma trận. |

---

## 8. Kết luận & Khuyến nghị

Kế hoạch tái thiết kế giao diện UI 3 Cột phiên bản `1.4.1 (Final Production Ready)` là bản đặc tả kỹ thuật hoàn thiện và chuẩn xác nhất sau 9 vòng kiểm chứng, đối chiếu toàn diện với mã nguồn backend FastAPI:
- Đồng bộ tuyệt đối **tỷ lệ render DPI (`scale = dpi / 72`)** và **bắt buộc `filename` trong `FormData`**.
- Tích hợp cơ chế **hủy request an toàn (`AbortController`)**, **thu hồi bộ nhớ đệm trang (`Page Eviction`)** và **tự động thăm dò trạng thái kết nối thông minh (`Smart Health Polling`)**.
- Khớp 100% danh mục **`error_code`** thực tế trong codebase và làm rõ bản chất dữ liệu **raw OCR vs fused Markdown**.
- Bổ sung **Retry Guard** bảo vệ máy chủ và chỉ dẫn cài đặt môi trường cho `pdfplumber` (`[pdf]`).

Tài liệu này đạt chuẩn chất lượng cao nhất để đội ngũ bắt tay triển khai mã nguồn tại thư mục `ui/`.
