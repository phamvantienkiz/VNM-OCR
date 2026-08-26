/**
 * Vietnamese OCR Studio — Main Application Controller
 * Conforms to DOC-PLAN-UI-001 v1.4.1
 */

import {
    AppState,
    EventBus,
    updateFilteredLinesAndMetrics,
    buildPageCacheKey,
    resetResultState,
} from './state.js';

import {
    checkHealth,
    startHealthPolling,
    stopHealthPolling,
    abortCurrentRequest,
    sendOcrRequest,
    sendDocumentRequest,
    sanitizeHtml,
} from './api.js';

import {
    loadPdfDocument,
    renderPdfPageToCanvas,
    exportPdfPageToBlob,
    renderPdfThumbnail,
    evictDistantPages,
} from './pdf-loader.js';

import {
    renderBoundingBoxes,
    highlightBbox,
    clearBboxHighlight,
    clearBboxOverlay,
} from './bbox-renderer.js';

// DOM Element References
const dom = {};

/**
 * Khởi tạo ứng dụng khi DOM đã nạp hoàn tất
 */
document.addEventListener('DOMContentLoaded', () => {
    cacheDomElements();
    bindEventListeners();
    initEventBusHandlers();
    startHealthPolling();
});

/**
 * Cache các phần tử DOM thường dùng
 */
function cacheDomElements() {
    dom.apiStatus = document.getElementById('api-status');

    // Cột 1
    dom.dropZone = document.getElementById('drop-zone');
    dom.fileInput = document.getElementById('file-input');
    dom.fileInfoCard = document.getElementById('file-info-card');
    dom.fileTypeIcon = document.getElementById('file-type-icon');
    dom.fileName = document.getElementById('file-name');
    dom.fileMeta = document.getElementById('file-meta');
    dom.changeFileBtn = document.getElementById('change-file-btn');

    dom.modeOcr = document.getElementById('mode-ocr');
    dom.modeDoc = document.getElementById('mode-doc');
    dom.docOptionsGroup = document.getElementById('document-options-group');
    dom.dpi72 = document.getElementById('dpi-72');
    dom.dpi150 = document.getElementById('dpi-150');
    dom.dpi300 = document.getElementById('dpi-300');
    dom.extractTablesCheckbox = document.getElementById('extract-tables-checkbox');

    dom.confidenceSlider = document.getElementById('confidence-slider');
    dom.confidenceValue = document.getElementById('confidence-value');

    dom.runOcrBtn = document.getElementById('run-ocr-btn');
    dom.runOcrSpinner = document.getElementById('run-ocr-spinner');
    dom.runOcrIcon = document.getElementById('run-ocr-icon');
    dom.runOcrText = document.getElementById('run-ocr-text');
    dom.resetBtn = document.getElementById('reset-btn');

    dom.pdfThumbnailsContainer = document.getElementById('pdf-thumbnails-container');
    dom.pdfPageCountBadge = document.getElementById('pdf-page-count-badge');
    dom.pdfThumbnailsList = document.getElementById('pdf-thumbnails-list');

    // Cột 2
    dom.zoomOutBtn = document.getElementById('zoom-out-btn');
    dom.zoomResetBtn = document.getElementById('zoom-reset-btn');
    dom.zoomInBtn = document.getElementById('zoom-in-btn');
    dom.zoomFitBtn = document.getElementById('zoom-fit-btn');
    dom.zoomRatioBadge = document.getElementById('zoom-ratio-badge');

    dom.viewerPdfNav = document.getElementById('viewer-pdf-nav');
    dom.prevPageBtn = document.getElementById('prev-page-btn');
    dom.viewerPageIndicator = document.getElementById('viewer-page-indicator');
    dom.nextPageBtn = document.getElementById('next-page-btn');
    dom.toggleBboxBtn = document.getElementById('toggle-bbox-btn');

    dom.viewportContainer = document.getElementById('viewport-container');
    dom.viewportEmptyState = document.getElementById('viewport-empty-state');
    dom.panZoomContainer = document.getElementById('pan-zoom-container');
    dom.imageWrapper = document.getElementById('image-wrapper');
    dom.previewImage = document.getElementById('preview-image');
    dom.pdfRenderCanvas = document.getElementById('pdf-render-canvas');
    dom.bboxOverlay = document.getElementById('bbox-overlay');

    dom.viewerFileDim = document.getElementById('viewer-file-dim');
    dom.viewerStatusText = document.getElementById('viewer-status-text');

    // Cột 3
    dom.metricTime = document.getElementById('metric-time');
    dom.metricLines = document.getElementById('metric-lines');
    dom.metricConfidence = document.getElementById('metric-confidence');

    dom.tabMarkdown = document.getElementById('tab-markdown');
    dom.tabLines = document.getElementById('tab-lines');
    dom.tabJson = document.getElementById('tab-json');

    dom.outputMarkdownTextarea = document.getElementById('output-markdown-textarea');
    dom.markdownEmptyState = document.getElementById('markdown-empty-state');
    dom.linesListContainer = document.getElementById('lines-list-container');
    dom.linesEmptyState = document.getElementById('lines-empty-state');
    dom.outputJsonView = document.getElementById('output-json-view');
    dom.jsonEmptyState = document.getElementById('json-empty-state');

    dom.copyTextBtn = document.getElementById('copy-text-btn');
    dom.downloadTxtBtn = document.getElementById('download-txt-btn');
    dom.downloadJsonBtn = document.getElementById('download-json-btn');
    dom.toastContainer = document.getElementById('toast-container');
}

/**
 * Gắn kết các sự kiện tương tác DOM
 */
function bindEventListeners() {
    // 1. Drag and drop & File Select
    dom.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dom.dropZone.classList.add('dragover');
    });

    dom.dropZone.addEventListener('dragleave', () => {
        dom.dropZone.classList.remove('dragover');
    });

    dom.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dom.dropZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    dom.dropZone.addEventListener('click', () => dom.fileInput.click());
    dom.dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            dom.fileInput.click();
        }
    });

    dom.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    dom.changeFileBtn.addEventListener('click', () => dom.fileInput.click());

    // 2. Mode Switches & Document Options
    dom.modeOcr.addEventListener('change', () => {
        AppState.config.endpoint = '/api/v1/ocr';
        dom.docOptionsGroup.classList.add('d-none');
        dom.runOcrText.textContent = 'Chạy nhận dạng OCR';
    });

    dom.modeDoc.addEventListener('change', () => {
        AppState.config.endpoint = '/api/v1/document/extract';
        dom.docOptionsGroup.classList.remove('d-none');
        dom.runOcrText.textContent = 'Trích xuất tài liệu';
    });

    const dpiRadios = [dom.dpi72, dom.dpi150, dom.dpi300];
    dpiRadios.forEach(radio => {
        if (radio) {
            radio.addEventListener('change', (e) => {
                AppState.config.resolution = Number(e.target.value) || 150;
                if (AppState.file.type === 'pdf') {
                    renderCurrentPdfPage();
                }
            });
        }
    });

    dom.extractTablesCheckbox.addEventListener('change', (e) => {
        AppState.config.extractTables = e.target.checked;
    });

    // 3. Confidence Threshold Slider
    dom.confidenceSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        AppState.config.confidenceThreshold = val;
        dom.confidenceValue.textContent = `≥ ${val.toFixed(2)}`;
        onConfidenceThresholdChanged();
    });

    // 4. Action CTA Buttons
    dom.runOcrBtn.addEventListener('click', () => submitOcrRequest());
    dom.resetBtn.addEventListener('click', () => handleAppReset());

    // 5. Viewport Controls (Zoom/Pan/BBox)
    dom.zoomInBtn.addEventListener('click', () => changeZoom(0.2));
    dom.zoomOutBtn.addEventListener('click', () => changeZoom(-0.2));
    dom.zoomResetBtn.addEventListener('click', () => setZoom(1.0));
    dom.zoomFitBtn.addEventListener('click', () => fitZoomToViewport());
    dom.toggleBboxBtn.addEventListener('click', () => toggleBboxDisplay());

    // 6. PDF Page Navigation Buttons
    dom.prevPageBtn.addEventListener('click', () => navigatePdfPage(-1));
    dom.nextPageBtn.addEventListener('click', () => navigatePdfPage(1));

    // 7. Export Toolbar Buttons
    dom.copyTextBtn.addEventListener('click', () => handleCopyText());
    dom.downloadTxtBtn.addEventListener('click', () => handleDownloadTxt());
    dom.downloadJsonBtn.addEventListener('click', () => handleDownloadJson());

    // 8. Window Resize Event for responsive BBox redrawing
    window.addEventListener('resize', () => {
        redrawActiveBboxes();
    });
}

/**
 * Đăng ký các sự kiện trên EventBus
 */
function initEventBusHandlers() {
    // 1. Cập nhật Badge trạng thái máy chủ
    EventBus.on('server:status', ({ connected, status, modelsReady }) => {
        AppState.server = { connected, status, modelsReady, lastChecked: new Date() };

        dom.apiStatus.className = 'status-badge d-flex align-items-center gap-1.5 px-2.5 py-1 rounded-pill';
        const textSpan = dom.apiStatus.querySelector('.status-text');

        if (connected && modelsReady) {
            dom.apiStatus.classList.add('status-ready');
            textSpan.textContent = 'Connected & Ready';
            dom.apiStatus.title = 'Máy chủ và toàn bộ mô hình AI đã sẵn sàng.';
        } else if (connected && !modelsReady) {
            dom.apiStatus.classList.add('status-warning');
            textSpan.textContent = 'Models Initializing...';
            dom.apiStatus.title = 'Máy chủ đã kết nối, mô hình AI đang được khởi tạo.';
        } else {
            dom.apiStatus.classList.add('status-danger');
            textSpan.textContent = 'API Disconnected';
            dom.apiStatus.title = 'Không kết nối được với máy chủ backend.';
        }
    });

    // 2. Sự kiện tải tệp mới (Bắt buộc hủy request cũ)
    EventBus.on('file:loaded', ({ file, type }) => {
        abortCurrentRequest();
        AppState.pageCache.clear();
        resetResultState();
        clearBboxOverlay();
        renderResultViews();
    });

    // 3. Sự kiện hover qua lại giữa BBox và dòng văn bản
    EventBus.on('bbox:hover', ({ id, hover }) => {
        const itemCard = document.querySelector(`.line-item-card[data-line-id="${id}"]`);
        if (itemCard) {
            if (hover) {
                itemCard.classList.add('active');
            } else {
                itemCard.classList.remove('active');
            }
        }
    });

    EventBus.on('bbox:select', ({ id }) => {
        const itemCard = document.querySelector(`.line-item-card[data-line-id="${id}"]`);
        if (itemCard) {
            // Chuyển sang Tab 2 nếu đang ở tab khác
            const tabTrigger = new bootstrap.Tab(dom.tabLines);
            tabTrigger.show();
            itemCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            itemCard.classList.add('active');
        }
    });
}

/**
 * Xử lý khi người dùng chọn một tệp mới
 * @param {File} file
 */
async function handleFileSelection(file) {
    if (!file) return;

    // Validate kích thước tệp (20MB)
    const maxSizeBytes = 20 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
        showToast('error', 'Dung lượng tệp tin vượt quá 20 MB. Vui lòng chọn tệp nhỏ hơn.');
        return;
    }

    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|webp|tiff?|bmp)$/i.test(file.name);

    if (!isPdf && !isImage) {
        showToast('error', 'Định dạng tệp không được hỗ trợ. Vui lòng chọn tệp PDF hoặc Hình ảnh.');
        return;
    }

    // Phát sự kiện file:loaded để hủy request cũ và dọn cache
    EventBus.emit('file:loaded', { file, type: isPdf ? 'pdf' : 'image' });

    AppState.file.raw = file;
    AppState.file.name = file.name;
    AppState.file.size = file.size;
    AppState.file.type = isPdf ? 'pdf' : 'image';
    AppState.file.currentPage = 1;

    updateFileMetadataCard();

    if (isImage) {
        await processSingleImage(file);
    } else if (isPdf) {
        await processPdfDocument(file);
    }

    dom.runOcrBtn.disabled = false;
}

/**
 * Xử lý nạp ảnh đơn
 * @param {File} file
 */
async function processSingleImage(file) {
    dom.pdfThumbnailsContainer.classList.add('d-none');
    dom.viewerPdfNav.classList.add('d-none');

    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            AppState.file.dimensions = {
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
            };

            // Cảnh báo nếu kích thước ảnh quá lớn (> 8000px)
            validateImageDimensions(img.naturalWidth, img.naturalHeight);

            dom.previewImage.src = e.target.result;
            dom.previewImage.classList.remove('d-none');
            dom.pdfRenderCanvas.classList.add('d-none');

            dom.viewportEmptyState.classList.add('d-none');
            dom.panZoomContainer.classList.remove('d-none');

            dom.viewerFileDim.textContent = `Kích thước: ${img.naturalWidth} × ${img.naturalHeight} px`;
            dom.viewerStatusText.textContent = 'Ảnh đã sẵn sàng';
            setZoom(1.0);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

/**
 * Xử lý nạp tệp tài liệu PDF
 * @param {File} file
 */
async function processPdfDocument(file) {
    try {
        dom.viewerStatusText.textContent = 'Đang đọc tệp PDF...';
        const { doc, totalPages } = await loadPdfDocument(file);

        AppState.file.pdfDoc = doc;
        AppState.file.totalPages = totalPages;
        AppState.file.currentPage = 1;

        dom.pdfPageCountBadge.textContent = `${totalPages} trang`;
        dom.viewerPageIndicator.textContent = `Trang 1 / ${totalPages}`;

        // Hiển thị thanh điều hướng trang & danh sách thumbnail
        dom.viewerPdfNav.classList.remove('d-none');
        dom.pdfThumbnailsContainer.classList.remove('d-none');
        dom.previewImage.classList.add('d-none');
        dom.pdfRenderCanvas.classList.remove('d-none');

        updatePdfNavButtons();

        // Render danh sách thumbnail
        renderPdfThumbnailsList(doc, totalPages);

        // Render trang đầu tiên
        await renderCurrentPdfPage();

        dom.viewportEmptyState.classList.add('d-none');
        dom.panZoomContainer.classList.remove('d-none');
        setZoom(1.0);
    } catch (err) {
        console.error('[App] PDF load error:', err);
        showToast('error', `Không thể nạp tệp PDF: ${err.message}`);
    }
}

/**
 * Render trang PDF hiện tại lên Canvas
 */
async function renderCurrentPdfPage() {
    if (!AppState.file.pdfDoc) return;

    dom.viewerStatusText.textContent = `Đang render trang ${AppState.file.currentPage}...`;
    const dims = await renderPdfPageToCanvas(
        AppState.file.pdfDoc,
        AppState.file.currentPage,
        AppState.config.resolution,
        dom.pdfRenderCanvas
    );

    AppState.file.dimensions = {
        naturalWidth: dims.width,
        naturalHeight: dims.height,
    };

    dom.viewerFileDim.textContent = `Trang ${AppState.file.currentPage} (${AppState.config.resolution} DPI): ${dims.width} × ${dims.height} px`;
    dom.viewerStatusText.textContent = 'Trang PDF sẵn sàng';

    // Eviction bộ nhớ RAM
    evictDistantPages(AppState.file.currentPage);

    // Kiểm tra và khôi phục kết quả từ Cache nếu có
    const cacheKey = buildPageCacheKey(AppState.file.currentPage);
    if (AppState.pageCache.has(cacheKey)) {
        AppState.activeResult = AppState.pageCache.get(cacheKey);
        renderResultViews();
        redrawActiveBboxes();
    } else {
        resetResultState();
        clearBboxOverlay();
        renderResultViews();
    }
}

/**
 * Render danh sách thumbnails của toàn bộ trang PDF
 * @param {Object} pdfDoc
 * @param {number} totalPages
 */
async function renderPdfThumbnailsList(pdfDoc, totalPages) {
    dom.pdfThumbnailsList.innerHTML = '';

    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
        const itemDiv = document.createElement('div');
        itemDiv.className = `pdf-thumbnail-item p-1.5 ${pageNum === 1 ? 'active' : ''}`;
        itemDiv.dataset.pageNum = String(pageNum);

        const pageLabel = document.createElement('div');
        pageLabel.className = 'd-flex justify-content-between align-items-center mb-1 text-muted';
        pageLabel.style.fontSize = '0.68rem';
        pageLabel.innerHTML = `<span>Trang ${pageNum}</span>`;

        itemDiv.appendChild(pageLabel);

        // Async render thumbnail
        renderPdfThumbnail(pdfDoc, pageNum, 140).then(({ canvas }) => {
            itemDiv.appendChild(canvas);
        });

        itemDiv.addEventListener('click', () => {
            if (pageNum !== AppState.file.currentPage) {
                AppState.file.currentPage = pageNum;
                updatePdfNavButtons();
                renderCurrentPdfPage();
            }
        });

        dom.pdfThumbnailsList.appendChild(itemDiv);
    }
}

/**
 * Điều hướng trang PDF trước/sau
 * @param {number} delta - (-1 hoặc 1)
 */
function navigatePdfPage(delta) {
    const newPage = AppState.file.currentPage + delta;
    if (newPage >= 1 && newPage <= AppState.file.totalPages) {
        AppState.file.currentPage = newPage;
        updatePdfNavButtons();
        renderCurrentPdfPage();
    }
}

/**
 * Cập nhật trạng thái các nút điều hướng PDF
 */
function updatePdfNavButtons() {
    const curr = AppState.file.currentPage;
    const total = AppState.file.totalPages;

    dom.viewerPageIndicator.textContent = `Trang ${curr} / ${total}`;
    dom.prevPageBtn.disabled = curr <= 1;
    dom.nextPageBtn.disabled = curr >= total;

    // Highlight thumbnail tương ứng
    const thumbnails = dom.pdfThumbnailsList.querySelectorAll('.pdf-thumbnail-item');
    thumbnails.forEach(el => {
        if (Number(el.dataset.pageNum) === curr) {
            el.classList.add('active');
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            el.classList.remove('active');
        }
    });
}

/**
 * Kiểm tra kích thước hình ảnh và hiển thị cảnh báo nếu quá lớn
 * @param {number} width
 * @param {number} height
 */
function validateImageDimensions(width, height) {
    if (width > 8000 || height > 8000) {
        showToast('warning', `Ảnh có kích thước rất lớn (${width}×${height}px). Quá trình OCR có thể mất nhiều thời gian hơn bình thường.`);
    }
}

/**
 * Cập nhật thông tin thẻ tệp đã chọn ở Cột 1
 */
function updateFileMetadataCard() {
    dom.fileInfoCard.classList.remove('d-none');
    dom.fileName.textContent = AppState.file.name;

    const sizeMb = (AppState.file.size / (1024 * 1024)).toFixed(2);
    if (AppState.file.type === 'pdf') {
        dom.fileTypeIcon.className = 'bi bi-file-earmark-pdf text-danger fs-5 flex-shrink-0';
        dom.fileMeta.textContent = `${sizeMb} MB · PDF Document`;
    } else {
        dom.fileTypeIcon.className = 'bi bi-file-earmark-image text-indigo-600 fs-5 flex-shrink-0';
        dom.fileMeta.textContent = `${sizeMb} MB · Hình ảnh`;
    }
}

/**
 * Gửi yêu cầu OCR hoặc Document Extraction tới máy chủ
 */
async function submitOcrRequest() {
    if (!AppState.file.raw) {
        showToast('warning', 'Vui lòng chọn tệp tin cần nhận dạng trước.');
        return;
    }

    // Health Guard: Kiểm tra backend trước khi gửi
    const health = await checkHealth();
    if (!health.connected) {
        showToast('error', 'Không kết nối được với máy chủ OCR. Vui lòng kiểm tra backend.');
        return;
    }
    if (!health.modelsReady) {
        showToast('warning', 'Mô hình AI đang khởi tạo (warmup). Vui lòng đợi trong giây lát...');
        return;
    }

    setLoadingState(true);
    const startTime = performance.now();

    try {
        let responseData = null;

        if (AppState.config.endpoint === '/api/v1/ocr') {
            // Chế độ OCR Đơn dòng
            if (AppState.file.type === 'image') {
                responseData = await sendOcrRequest(AppState.file.raw, AppState.file.name);
            } else {
                // Xuất canvas trang PDF hiện tại sang Blob PNG
                const { blob } = await exportPdfPageToBlob(
                    AppState.file.pdfDoc,
                    AppState.file.currentPage,
                    AppState.config.resolution
                );
                responseData = await sendOcrRequest(blob, `page_${AppState.file.currentPage}.png`);
            }
        } else {
            // Chế độ Document Extraction
            responseData = await sendDocumentRequest(
                AppState.file.raw,
                AppState.config.extractTables,
                AppState.config.resolution,
                AppState.file.name
            );
        }

        const elapsedMs = Math.round(performance.now() - startTime);

        // Chuẩn hóa và lưu trữ kết quả
        processApiResponseData(responseData, elapsedMs);

        // Lưu vào Cache cho trang hiện tại
        const cacheKey = buildPageCacheKey(AppState.file.currentPage);
        AppState.pageCache.set(cacheKey, { ...AppState.activeResult });

        showToast('success', 'Nhận dạng OCR thành công!');
    } catch (err) {
        if (err.isAborted) {
            console.info('[App] Request was aborted by user.');
        } else {
            console.error('[App] OCR Error:', err);
            showToast('error', err.message || 'Đã xảy ra lỗi khi chạy OCR.');
        }
    } finally {
        setLoadingState(false);
    }
}

/**
 * Chuẩn hóa payload trả về từ Backend sang AppState.activeResult
 * @param {Object} data
 * @param {number} elapsedMs
 */
function processApiResponseData(data, elapsedMs) {
    AppState.activeResult.isLoading = false;
    AppState.activeResult.elapsedMs = data.elapsed_ms || elapsedMs;
    AppState.activeResult.rawResponse = data;

    let textLines = [];
    let fullMarkdown = '';

    if (AppState.config.endpoint === '/api/v1/ocr') {
        // OcrResponse: { text_lines: [{ text, score, bbox }] }
        textLines = (data.text_lines || []).map((line, idx) => ({
            id: idx,
            text: line.text || '',
            score: line.score || 0,
            bbox: line.bbox || [],
            type: 'text',
        }));
        fullMarkdown = textLines.map(l => l.text).join('\n');
    } else {
        // DocumentResponse: { full_markdown, pages: [{ page_num, full_markdown, text_lines }] }
        const pages = data.pages || [];
        const currentPageData = pages.find(p => p.page_num === AppState.file.currentPage) || pages[0] || {};

        fullMarkdown = data.full_markdown || currentPageData.full_markdown || '';
        textLines = (currentPageData.text_lines || []).map((line, idx) => ({
            id: idx,
            text: line.text || '',
            score: line.score || 0,
            bbox: line.bbox || [],
            type: line.type || 'text',
        }));

        if (!fullMarkdown && textLines.length > 0) {
            fullMarkdown = textLines.map(l => l.text).join('\n');
        }
    }

    AppState.activeResult.textLines = textLines;
    AppState.activeResult.fullMarkdown = fullMarkdown;

    updateFilteredLinesAndMetrics();
    renderResultViews();
    redrawActiveBboxes();
}

/**
 * Render toàn bộ các view hiển thị kết quả (Metrics, Tab 1, Tab 2, Tab 3)
 */
function renderResultViews() {
    const { elapsedMs, fullMarkdown, filteredLines, avgConfidence, rawResponse } = AppState.activeResult;

    // 1. Render Metrics
    dom.metricTime.textContent = elapsedMs ? `${elapsedMs} ms` : '-- ms';
    dom.metricLines.textContent = filteredLines.length > 0 ? String(filteredLines.length) : '--';
    dom.metricConfidence.textContent = avgConfidence ? `${avgConfidence}%` : '--%';

    // 2. Render Tab 1: Full Markdown / Text
    if (fullMarkdown) {
        dom.markdownEmptyState.classList.add('d-none');
        dom.outputMarkdownTextarea.classList.remove('d-none');
        dom.outputMarkdownTextarea.value = fullMarkdown;
    } else {
        dom.markdownEmptyState.classList.remove('d-none');
        dom.outputMarkdownTextarea.classList.add('d-none');
        dom.outputMarkdownTextarea.value = '';
    }

    // 3. Render Tab 2: Line list with scores
    if (filteredLines && filteredLines.length > 0) {
        dom.linesEmptyState.classList.add('d-none');
        dom.linesListContainer.classList.remove('d-none');
        dom.linesListContainer.innerHTML = '';

        filteredLines.forEach((item) => {
            const lineCard = document.createElement('div');
            lineCard.className = 'line-item-card d-flex align-items-start justify-content-between gap-2';
            lineCard.dataset.lineId = String(item.id);

            const scorePercent = Math.round((item.score || 0) * 1000) / 10;
            let pillClass = 'confidence-high';
            if (scorePercent < 70) {
                pillClass = 'confidence-low';
            } else if (scorePercent < 90) {
                pillClass = 'confidence-mid';
            }

            lineCard.innerHTML = `
                <div class="d-flex align-items-start gap-2 flex-grow-1 text-truncate">
                    <span class="badge bg-slate-100 text-slate-600 border flex-shrink-0" style="font-size: 0.65rem;">#${item.id + 1}</span>
                    <span class="text-slate-800 text-truncate" style="font-size: 0.78rem;">${sanitizeHtml(item.text)}</span>
                </div>
                <span class="confidence-pill ${pillClass} flex-shrink-0">${scorePercent}%</span>
            `;

            // Line hover interaction
            lineCard.addEventListener('mouseenter', () => {
                highlightBbox(item.id);
                lineCard.classList.add('active');
            });

            lineCard.addEventListener('mouseleave', () => {
                clearBboxHighlight();
                lineCard.classList.remove('active');
            });

            dom.linesListContainer.appendChild(lineCard);
        });
    } else {
        dom.linesEmptyState.classList.remove('d-none');
        dom.linesListContainer.classList.add('d-none');
        dom.linesListContainer.innerHTML = '';
    }

    // 4. Render Tab 3: JSON Payload
    if (rawResponse) {
        dom.jsonEmptyState.classList.add('d-none');
        dom.outputJsonView.classList.remove('d-none');
        dom.outputJsonView.querySelector('code').textContent = JSON.stringify(rawResponse, null, 2);
    } else {
        dom.jsonEmptyState.classList.remove('d-none');
        dom.outputJsonView.classList.add('d-none');
        dom.outputJsonView.querySelector('code').textContent = '';
    }

    // 5. Cập nhật trạng thái Toolbar Export
    const hasData = Boolean(fullMarkdown || (filteredLines && filteredLines.length > 0));
    dom.copyTextBtn.disabled = !hasData;
    dom.downloadTxtBtn.disabled = !hasData;
    dom.downloadJsonBtn.disabled = !rawResponse;
}

/**
 * Vẽ lại các BBox trên Viewport dựa trên dữ liệu dòng hiện tại
 */
function redrawActiveBboxes() {
    const mediaEl = AppState.file.type === 'pdf' ? dom.pdfRenderCanvas : dom.previewImage;
    renderBoundingBoxes(dom.bboxOverlay, mediaEl, AppState.activeResult.filteredLines);
}

/**
 * Xử lý khi thay đổi Slider ngưỡng tin cậy
 */
function onConfidenceThresholdChanged() {
    updateFilteredLinesAndMetrics();
    renderResultViews();
    redrawActiveBboxes();
}

/**
 * Thiết lập trạng thái Loading cho nút CTA
 * @param {boolean} isLoading
 */
function setLoadingState(isLoading) {
    AppState.activeResult.isLoading = isLoading;
    dom.runOcrBtn.disabled = isLoading;

    if (isLoading) {
        dom.runOcrSpinner.classList.remove('d-none');
        dom.runOcrIcon.classList.add('d-none');
        dom.runOcrText.textContent = 'Đang xử lý AI...';
        dom.viewerStatusText.textContent = 'Đang chạy suy luận OCR...';
    } else {
        dom.runOcrSpinner.classList.add('d-none');
        dom.runOcrIcon.classList.remove('d-none');
        dom.runOcrText.textContent = AppState.config.endpoint === '/api/v1/ocr' ? 'Chạy nhận dạng OCR' : 'Trích xuất tài liệu';
        dom.viewerStatusText.textContent = 'Hoàn tất';
    }
}

/**
 * Đặt lại toàn bộ giao diện và dữ liệu (Reset)
 */
function handleAppReset() {
    abortCurrentRequest();

    AppState.file = {
        raw: null,
        name: '',
        size: 0,
        type: 'unknown',
        pdfDoc: null,
        totalPages: 0,
        currentPage: 1,
        dimensions: { naturalWidth: 0, naturalHeight: 0 },
        pageDataUrls: new Map(),
    };

    AppState.pageCache.clear();
    resetResultState();
    clearBboxOverlay();

    dom.fileInput.value = '';
    dom.fileInfoCard.classList.add('d-none');
    dom.pdfThumbnailsContainer.classList.add('d-none');
    dom.pdfThumbnailsList.innerHTML = '';
    dom.viewerPdfNav.classList.add('d-none');

    dom.viewportEmptyState.classList.remove('d-none');
    dom.panZoomContainer.classList.add('d-none');
    dom.previewImage.src = '';
    dom.runOcrBtn.disabled = true;

    dom.viewerFileDim.textContent = 'Kích thước: -- × -- px';
    dom.viewerStatusText.textContent = 'Sẵn sàng';

    setZoom(1.0);
    renderResultViews();

    showToast('info', 'Đã làm mới giao diện.');
}

/**
 * Bật / Tắt hiển thị Bounding Box
 */
function toggleBboxDisplay() {
    AppState.config.showBBox = !AppState.config.showBBox;
    dom.toggleBboxBtn.classList.toggle('active', AppState.config.showBBox);
    redrawActiveBboxes();
}

/**
 * Điều chỉnh độ thu phóng (Zoom)
 * @param {number} delta
 */
function changeZoom(delta) {
    const newZoom = Math.max(0.25, Math.min(3.0, AppState.config.zoomScale + delta));
    setZoom(newZoom);
}

/**
 * Đặt tỷ lệ Zoom cụ thể
 * @param {number} zoom
 */
function setZoom(zoom) {
    AppState.config.zoomScale = Math.round(zoom * 100) / 100;
    dom.zoomRatioBadge.textContent = `${Math.round(AppState.config.zoomScale * 100)}%`;
    dom.panZoomContainer.style.transform = `scale(${AppState.config.zoomScale})`;
    redrawActiveBboxes();
}

/**
 * Tự động căn chỉnh Zoom vừa khung nhìn Viewport
 */
function fitZoomToViewport() {
    const viewportWidth = dom.viewportContainer.clientWidth - 40;
    const naturalWidth = AppState.file.dimensions.naturalWidth || 1;

    if (viewportWidth > 0 && naturalWidth > 0) {
        const fitScale = Math.min(1.5, Math.max(0.25, viewportWidth / naturalWidth));
        setZoom(fitScale);
    }
}

/**
 * Sao chép văn bản kết quả vào Clipboard
 */
async function handleCopyText() {
    const text = dom.outputMarkdownTextarea.value || '';
    if (!text) {
        showToast('warning', 'Không có nội dung để sao chép.');
        return;
    }

    try {
        await navigator.clipboard.writeText(text);
        showToast('success', 'Đã sao chép nội dung vào Clipboard!');
    } catch (err) {
        showToast('error', 'Không thể truy cập Clipboard.');
    }
}

/**
 * Tải xuống tệp .TXT / .MD
 */
function handleDownloadTxt() {
    const text = dom.outputMarkdownTextarea.value || '';
    if (!text) return;

    const ext = AppState.config.endpoint === '/api/v1/document/extract' ? 'md' : 'txt';
    const baseName = (AppState.file.name || 'document').replace(/\.[^/.]+$/, '');
    const filename = `${baseName}_ocr.${ext}`;

    downloadBlob(new Blob([text], { type: 'text/plain;charset=utf-8' }), filename);
    showToast('success', `Đã tải xuống ${filename}`);
}

/**
 * Tải xuống tệp .JSON
 */
function handleDownloadJson() {
    const json = AppState.activeResult.rawResponse;
    if (!json) return;

    const baseName = (AppState.file.name || 'document').replace(/\.[^/.]+$/, '');
    const filename = `${baseName}_response.json`;

    downloadBlob(new Blob([JSON.stringify(json, null, 2)], { type: 'application/json;charset=utf-8' }), filename);
    showToast('success', `Đã tải xuống ${filename}`);
}

/**
 * Helper tải xuống tệp Blob trên trình duyệt
 * @param {Blob} blob
 * @param {string} filename
 */
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Hiển thị thông báo Toast góc dưới màn hình
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {string} message
 */
export function showToast(type = 'info', message = '') {
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center border-0 show mb-2 shadow-lg';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    let bgClass = 'text-bg-secondary';
    let iconClass = 'bi-info-circle';

    if (type === 'success') {
        bgClass = 'text-bg-success';
        iconClass = 'bi-check-circle';
    } else if (type === 'error') {
        bgClass = 'text-bg-danger';
        iconClass = 'bi-exclamation-triangle';
    } else if (type === 'warning') {
        bgClass = 'text-bg-warning text-dark';
        iconClass = 'bi-exclamation-circle';
    }

    toastEl.classList.add(...bgClass.split(' '));

    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body d-flex align-items-center gap-2" style="font-size: 0.8rem;">
                <i class="bi ${iconClass} fs-6 flex-shrink-0"></i>
                <span>${sanitizeHtml(message)}</span>
            </div>
            <button type="button" class="btn-close ${type === 'warning' ? '' : 'btn-close-white'} me-2 m-auto" data-bs-dismiss="toast" aria-label="Đóng"></button>
        </div>
    `;

    dom.toastContainer.appendChild(toastEl);

    setTimeout(() => {
        toastEl.classList.remove('show');
        setTimeout(() => toastEl.remove(), 300);
    }, 4500);
}
