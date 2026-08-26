/**
 * Vietnamese OCR Studio — API Service & Network Layer
 * Conforms to DOC-PLAN-UI-001 v1.4.1 (Error Matrix, Health Polling, AbortController)
 */

import { EventBus } from './state.js';

// Base API configuration (relative path for microservice deployment)
const API_BASE_URL = '';

// In-flight AbortController singleton
let _activeController = null;

// Health Polling Timer singleton
let _healthPollTimer = null;

/**
 * Hủy bỏ request đang chạy dở dang
 */
export function abortCurrentRequest() {
    if (_activeController) {
        try {
            _activeController.abort();
        } catch (e) {
            console.warn('[API] Could not abort controller:', e);
        }
        _activeController = null;
    }
}

/**
 * Kiểm tra trạng thái máy chủ và mô hình AI (/api/v1/health)
 * @returns {Promise<{connected: boolean, status: string, modelsReady: boolean, data: Object|null}>}
 */
export async function checkHealth() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 6000);

        const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            return { connected: false, status: 'error', modelsReady: false, data: null };
        }

        const data = await response.json();
        const isOk = data.status === 'ok';
        const modelsReady = Boolean(data.models_ready);

        return {
            connected: isOk,
            status: isOk ? (modelsReady ? 'ok' : 'degraded') : 'error',
            modelsReady: modelsReady,
            data: data,
        };
    } catch (err) {
        return { connected: false, status: 'error', modelsReady: false, data: null };
    }
}

/**
 * Bắt đầu cơ chế Smart Health Polling tự động kiểm tra server mỗi 5s
 * khi chưa kết nối hoặc mô hình đang nạp (warmup)
 */
export async function startHealthPolling() {
    stopHealthPolling();

    const result = await checkHealth();
    EventBus.emit('server:status', result);

    // Nếu chưa sẵn sàng hoặc model đang nạp, tiếp tục thăm dò sau 5s
    if (!result.connected || !result.modelsReady) {
        _healthPollTimer = setTimeout(startHealthPolling, 5000);
    }
}

/**
 * Ngắt timer polling kiểm tra sức khỏe máy chủ
 */
export function stopHealthPolling() {
    if (_healthPollTimer) {
        clearTimeout(_healthPollTimer);
        _healthPollTimer = null;
    }
}

/**
 * Gửi yêu cầu nhận dạng OCR đơn ảnh (/api/v1/ocr)
 * @param {Blob|File} fileOrBlob - File hoặc Blob hình ảnh
 * @param {string} [filename='image.png'] - Tên tệp gửi kèm
 * @returns {Promise<Object>}
 */
export async function sendOcrRequest(fileOrBlob, filename = 'image.png') {
    abortCurrentRequest();
    _activeController = new AbortController();

    const formData = new FormData();
    // Bắt buộc cung cấp filename để FastAPI UploadFile validation không ném HTTP 400
    formData.append('file', fileOrBlob, filename);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/ocr`, {
            method: 'POST',
            body: formData,
            signal: _activeController.signal,
        });

        return await handleApiResponse(response);
    } catch (err) {
        handleNetworkError(err);
    } finally {
        _activeController = null;
    }
}

/**
 * Gửi yêu cầu trích xuất toàn diện tài liệu/bố cục (/api/v1/document/extract)
 * @param {File|Blob} fileOrBlob - File tài liệu hoặc hình ảnh
 * @param {boolean} [extractTables=true] - Bật nhận diện TSR
 * @param {number} [resolution=150] - Độ phân giải render PDF (72 - 300 DPI)
 * @param {string} [filename='document.pdf'] - Tên tệp gửi kèm
 * @returns {Promise<Object>}
 */
export async function sendDocumentRequest(fileOrBlob, extractTables = true, resolution = 150, filename = 'document.pdf') {
    abortCurrentRequest();
    _activeController = new AbortController();

    // Ràng buộc resolution trong khoảng 72 đến 300
    const clampedRes = Math.min(300, Math.max(72, Number(resolution) || 150));

    const url = new URL(`${API_BASE_URL}/api/v1/document/extract`, window.location.origin);
    url.searchParams.set('extract_tables', String(Boolean(extractTables)));
    url.searchParams.set('resolution', String(clampedRes));

    const actualFilename = fileOrBlob.name || filename;
    const formData = new FormData();
    formData.append('file', fileOrBlob, actualFilename);

    try {
        const response = await fetch(url.toString(), {
            method: 'POST',
            body: formData,
            signal: _activeController.signal,
        });

        return await handleApiResponse(response);
    } catch (err) {
        handleNetworkError(err);
    } finally {
        _activeController = null;
    }
}

/**
 * Xử lý phản hồi API và ánh xạ bảng mã lỗi chi tiết (Error Response Matrix)
 * @param {Response} response
 * @returns {Promise<Object>}
 */
async function handleApiResponse(response) {
    if (response.ok) {
        return await response.json();
    }

    let errorData = null;
    try {
        errorData = await response.json();
    } catch (_) {
        errorData = { detail: response.statusText };
    }

    const detail = errorData?.detail || '';
    const errorCode = errorData?.error_code || '';
    const status = response.status;

    let userMessage = 'Đã xảy ra lỗi khi xử lý yêu cầu.';

    // Error Matrix mapping
    if (status === 400) {
        if (errorCode === 'INVALID_FILE_FORMAT' || detail.includes('format')) {
            userMessage = 'Định dạng tệp tin không được hỗ trợ. Vui lòng chọn tệp PDF hoặc ảnh hợp lệ.';
        } else if (errorCode === 'INVALID_VALUE' || detail.includes('empty')) {
            userMessage = 'Tệp tin tải lên bị rỗng hoặc tham số không hợp lệ.';
        } else {
            userMessage = `Yêu cầu không hợp lệ (HTTP 400): ${detail || 'Dữ liệu đầu vào sai quy chuẩn.'}`;
        }
    } else if (status === 413) {
        userMessage = 'Dung lượng tệp tin vượt quá giới hạn tối đa cho phép (20 MB).';
    } else if (status === 422) {
        userMessage = 'Tham số đầu vào không đúng định dạng kiểm tra (Validation Error).';
    } else if (status === 500) {
        if (errorCode === 'MODEL_NOT_FOUND') {
            userMessage = 'Máy chủ chưa tìm thấy tệp trọng số mô hình AI ONNX. Vui lòng kiểm tra thư mục backend/models/.';
        } else if (errorCode === 'INFERENCE_ERROR') {
            userMessage = 'Đã xảy ra lỗi trong quá trình suy luận mô hình AI (Inference Error).';
        } else {
            userMessage = `Lỗi nội bộ máy chủ (HTTP 500): ${detail || 'Vui lòng kiểm tra log server.'}`;
        }
    } else {
        userMessage = `Lỗi máy chủ (HTTP ${status}): ${detail || 'Vui lòng thử lại sau.'}`;
    }

    const err = new Error(userMessage);
    err.status = status;
    err.errorCode = errorCode;
    err.detail = detail;
    throw err;
}

/**
 * Xử lý lỗi kết nối hoặc hủy request
 * @param {Error} err
 */
function handleNetworkError(err) {
    if (err.name === 'AbortError') {
        const abortErr = new Error('Yêu cầu xử lý đã được hủy.');
        abortErr.isAborted = true;
        throw abortErr;
    }
    if (!navigator.onLine) {
        throw new Error('Mất kết nối mạng. Vui lòng kiểm tra lại đường truyền Internet.');
    }
    throw err;
}

/**
 * Làm sạch chuỗi trước khi chèn vào DOM chống tấn công XSS
 * @param {string} str
 * @returns {string}
 */
export function sanitizeHtml(str) {
    if (!str || typeof str !== 'string') return '';
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}
