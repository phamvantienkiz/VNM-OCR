/**
 * Vietnamese OCR Studio — PDF Processing Engine
 * Conforms to DOC-PLAN-UI-001 v1.4.1 (Dynamic DPI scale, Page Eviction, PDF.js 3.11.174)
 */

import { AppState, EventBus } from './state.js';

// Cấu hình PDF.js worker
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

/**
 * Chuyển đổi giá trị DPI sang tỷ lệ scale của PDF.js (Native PDF DPI là 72pt/inch)
 * @param {number} dpi - Chỉ số DPI (72, 150, 300...)
 * @returns {number} - Hệ số scale
 */
export function dpiToScale(dpi = 150) {
    const validDpi = Number(dpi) || 150;
    return validDpi / 72.0;
}

/**
 * Nạp tệp PDF từ File/Blob sang đối tượng PDFDocumentProxy
 * @param {File|Blob} file
 * @returns {Promise<{doc: Object, totalPages: number}>}
 */
export async function loadPdfDocument(file) {
    if (typeof pdfjsLib === 'undefined') {
        throw new Error('Thư viện PDF.js chưa được tải thành công.');
    }

    const arrayBuffer = await file.arrayBuffer();
    const loadingTask = pdfjsLib.getDocument({
        data: arrayBuffer,
        cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
        cMapPacked: true,
    });

    const doc = await loadingTask.promise;
    return {
        doc: doc,
        totalPages: doc.numPages,
    };
}

/**
 * Render một trang PDF trực tiếp lên thẻ HTML Canvas theo DPI chỉ định
 * @param {Object} pdfDoc - Đối tượng PDFDocumentProxy
 * @param {number} pageNum - Số trang (1-indexed)
 * @param {number} dpi - Chỉ số DPI (72, 150, 300)
 * @param {HTMLCanvasElement} targetCanvas - Canvas đích
 * @returns {Promise<{width: number, height: number}>}
 */
export async function renderPdfPageToCanvas(pdfDoc, pageNum, dpi, targetCanvas) {
    const page = await pdfDoc.getPage(pageNum);
    const scale = dpiToScale(dpi);
    const viewport = page.getViewport({ scale: scale });

    targetCanvas.width = Math.floor(viewport.width);
    targetCanvas.height = Math.floor(viewport.height);

    const ctx = targetCanvas.getContext('2d', { alpha: false });
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    const renderContext = {
        canvasContext: ctx,
        viewport: viewport,
    };

    await page.render(renderContext).promise;

    return {
        width: targetCanvas.width,
        height: targetCanvas.height,
    };
}

/**
 * Xuất một trang PDF sang đối tượng Blob ảnh PNG (sử dụng khi gửi OCR)
 * @param {Object} pdfDoc - Đối tượng PDFDocumentProxy
 * @param {number} pageNum - Số trang (1-indexed)
 * @param {number} dpi - Chỉ số DPI
 * @returns {Promise<{blob: Blob, dataUrl: string, width: number, height: number}>}
 */
export async function exportPdfPageToBlob(pdfDoc, pageNum, dpi) {
    const offscreenCanvas = document.createElement('canvas');
    const dims = await renderPdfPageToCanvas(pdfDoc, pageNum, dpi, offscreenCanvas);

    return new Promise((resolve, reject) => {
        offscreenCanvas.toBlob((blob) => {
            if (!blob) {
                reject(new Error(`Không thể xuất ảnh từ trang ${pageNum}`));
                return;
            }
            const dataUrl = offscreenCanvas.toDataURL('image/png');
            resolve({
                blob: blob,
                dataUrl: dataUrl,
                width: dims.width,
                height: dims.height,
            });
        }, 'image/png');
    });
}

/**
 * Tạo ảnh thumbnail kích thước nhỏ cho một trang PDF
 * @param {Object} pdfDoc - Đối tượng PDFDocumentProxy
 * @param {number} pageNum - Số trang (1-indexed)
 * @param {number} [targetWidth=140] - Chiều rộng thumbnail mong muốn
 * @returns {Promise<{canvas: HTMLCanvasElement, pageNum: number}>}
 */
export async function renderPdfThumbnail(pdfDoc, pageNum, targetWidth = 140) {
    const page = await pdfDoc.getPage(pageNum);
    const unscaledViewport = page.getViewport({ scale: 1.0 });
    const scale = targetWidth / unscaledViewport.width;
    const viewport = page.getViewport({ scale: scale });

    const canvas = document.createElement('canvas');
    canvas.className = 'pdf-thumbnail-canvas';
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);

    const ctx = canvas.getContext('2d');
    await page.render({
        canvasContext: ctx,
        viewport: viewport,
    }).promise;

    return { canvas, pageNum };
}

/**
 * Thu hồi bộ nhớ RAM: Chỉ giữ dataUrl chuỗi Base64 của các trang lân cận [currentPage - 2, currentPage + 2]
 * @param {number} currentPage - Trang hiện tại đang xem
 */
export function evictDistantPages(currentPage) {
    if (!AppState.file.pageDataUrls || AppState.file.pageDataUrls.size === 0) return;

    const minKeep = Math.max(1, currentPage - 2);
    const maxKeep = Math.min(AppState.file.totalPages, currentPage + 2);

    for (const [pageNum] of AppState.file.pageDataUrls.entries()) {
        if (pageNum < minKeep || pageNum > maxKeep) {
            AppState.file.pageDataUrls.delete(pageNum);
        }
    }
}
