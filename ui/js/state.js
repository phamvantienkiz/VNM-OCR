/**
 * Vietnamese OCR Studio — Application State & Event Bus
 * Conforms to DOC-PLAN-UI-001 v1.4.1
 */

/**
 * Global reactive application state
 */
export const AppState = {
    // Máy chủ backend
    server: {
        status: 'unknown',     // 'ok' | 'degraded' | 'error' | 'unknown'
        connected: false,
        modelsReady: false,
        lastChecked: null,
    },

    // Tệp tài liệu người dùng tải lên
    file: {
        raw: null,             // File object
        name: '',
        size: 0,
        type: 'unknown',       // 'image' | 'pdf' | 'unknown'
        pdfDoc: null,          // PDFDocumentProxy instance
        totalPages: 0,
        currentPage: 1,
        dimensions: { naturalWidth: 0, naturalHeight: 0 },
        pageDataUrls: new Map(), // pageNum -> dataUrl (Base64 string)
    },

    // Cấu hình tham số xử lý
    config: {
        endpoint: '/api/v1/ocr', // '/api/v1/ocr' | '/api/v1/document/extract'
        resolution: 150,         // 72 | 150 | 300 (DPI)
        extractTables: true,     // boolean
        confidenceThreshold: 0.50, // 0.50 to 1.00
        showBBox: true,          // boolean
        zoomScale: 1.0,          // Zoom ratio (0.25 to 3.0)
    },

    // Dữ liệu kết quả xử lý của trang/ảnh hiện tại
    activeResult: {
        isLoading: false,
        elapsedMs: 0,
        rawResponse: null,       // Payload JSON gốc từ backend
        fullMarkdown: '',        // Markdown kết quả
        textLines: [],           // [{ id, text, score, bbox }]
        filteredLines: [],       // Danh sách dòng đã lọc theo threshold
        avgConfidence: 0,        // Điểm tin cậy TB (0 - 100%)
    },

    // Cache kết quả xử lý theo từng trang PDF
    pageCache: new Map(),
};

/**
 * Event Bus publish/subscribe pattern with error isolation
 */
class SimpleEventBus {
    constructor() {
        this.listeners = new Map();
    }

    /**
     * Đăng ký lắng nghe sự kiện
     * @param {string} event - Tên sự kiện
     * @param {Function} callback - Hàm xử lý sự kiện
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }

    /**
     * Hủy đăng ký lắng nghe sự kiện
     * @param {string} event - Tên sự kiện
     * @param {Function} callback - Hàm xử lý sự kiện
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

    /**
     * Phát sự kiện tới tất cả các listener đã đăng ký
     * @param {string} event - Tên sự kiện
     * @param {*} data - Dữ liệu kèm theo
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            for (const callback of this.listeners.get(event)) {
                try {
                    callback(data);
                } catch (err) {
                    console.error(`[EventBus] Error in handler for event '${event}':`, err);
                }
            }
        }
    }
}

export const EventBus = new SimpleEventBus();

/**
 * Cập nhật danh sách dòng đã lọc và tính toán lại điểm tin cậy trung bình
 */
export function updateFilteredLinesAndMetrics() {
    const threshold = AppState.config.confidenceThreshold;
    const lines = AppState.activeResult.textLines || [];

    // Lọc theo ngưỡng
    AppState.activeResult.filteredLines = lines.filter(l => (l.score || 0) >= threshold);

    // Tính điểm tin cậy trung bình của các dòng đã lọc
    const filtered = AppState.activeResult.filteredLines;
    if (filtered.length > 0) {
        const sumScore = filtered.reduce((acc, curr) => acc + (curr.score || 0), 0);
        AppState.activeResult.avgConfidence = Math.round((sumScore / filtered.length) * 1000) / 10;
    } else {
        AppState.activeResult.avgConfidence = 0;
    }
}

/**
 * Tạo khóa cache cho trang hiện tại dựa trên cấu hình xử lý
 * @param {number} pageNum - Số thứ tự trang
 * @returns {string} - Chuỗi cache key
 */
export function buildPageCacheKey(pageNum = 1) {
    const { endpoint, resolution, extractTables } = AppState.config;
    return `${pageNum}_${endpoint}_${resolution}_${extractTables}`;
}

/**
 * Xóa toàn bộ trạng thái kết quả và bộ nhớ đệm
 */
export function resetResultState() {
    AppState.activeResult = {
        isLoading: false,
        elapsedMs: 0,
        rawResponse: null,
        fullMarkdown: '',
        textLines: [],
        filteredLines: [],
        avgConfidence: 0,
    };
}
