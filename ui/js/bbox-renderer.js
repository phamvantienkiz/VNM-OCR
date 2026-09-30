/**
 * Vietnamese OCR Studio — Bounding Box Rendering Engine
 * Conforms to DOC-PLAN-UI-001 v1.4.1 (Polygon & Rect Normalization, SVG Overlay, 2-Way Sync)
 */

import { AppState, EventBus } from './state.js';
import { sanitizeHtml } from './api.js';

/**
 * Chuẩn hóa BBox hỗ trợ cả 4-point polygon (OCR) và 4-float rect (Layout/Table)
 * @param {Array<Array<number>>|Array<number>} bbox
 * @returns {Array<Array<number>>} Mảng 4 điểm [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
 */
export function normalizeBbox(bbox) {
    if (!bbox || !Array.isArray(bbox)) {
        return [[0, 0], [0, 0], [0, 0], [0, 0]];
    }

    // Nếu đã là 4-point polygon [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    if (Array.isArray(bbox[0])) {
        return bbox;
    }

    // Nếu là 4-float rect [x1, y1, x2, y2]
    if (bbox.length === 4 && typeof bbox[0] === 'number') {
        const [x1, y1, x2, y2] = bbox;
        return [
            [x1, y1],
            [x2, y1],
            [x2, y2],
            [x1, y2],
        ];
    }

    return [[0, 0], [0, 0], [0, 0], [0, 0]];
}

/**
 * Vẽ lớp phủ Bounding Box dạng SVG lên container #bbox-overlay
 * @param {HTMLElement} overlayContainer - Thẻ chứa #bbox-overlay
 * @param {HTMLImageElement|HTMLCanvasElement} mediaElement - Thẻ ảnh hoặc Canvas đang hiển thị
 * @param {Array<Object>} lines - Danh sách các dòng văn bản [{ id, text, score, bbox }]
 */
export function renderBoundingBoxes(overlayContainer, mediaElement, lines) {
    if (!overlayContainer || !mediaElement) return;

    // Xóa nội dung vẽ cũ
    overlayContainer.innerHTML = '';

    if (!AppState.config.showBBox || !lines || lines.length === 0) {
        return;
    }

    // Lấy kích thước hiển thị thực tế
    const displayWidth = mediaElement.offsetWidth || mediaElement.width || 0;
    const displayHeight = mediaElement.offsetHeight || mediaElement.height || 0;

    // Lấy kích thước gốc của ảnh / trang PDF
    const naturalWidth = AppState.file.dimensions.naturalWidth || displayWidth || 1;
    const naturalHeight = AppState.file.dimensions.naturalHeight || displayHeight || 1;

    if (displayWidth === 0 || displayHeight === 0) return;

    // Tỷ lệ co dãn giữa kích thước hiển thị và kích thước gốc
    const scaleX = displayWidth / naturalWidth;
    const scaleY = displayHeight / naturalHeight;

    // Tạo SVG element bao phủ toàn bộ vùng ảnh
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('width', String(displayWidth));
    svg.setAttribute('height', String(displayHeight));
    svg.setAttribute('viewBox', `0 0 ${displayWidth} ${displayHeight}`);
    svg.style.position = 'absolute';
    svg.style.top = '0';
    svg.style.left = '0';
    svg.style.width = '100%';
    svg.style.height = '100%';
    svg.style.pointerEvents = 'auto';

    const tooltip = document.getElementById('bbox-tooltip');

    lines.forEach((item, index) => {
        const polyCoords = normalizeBbox(item.bbox);

        // Chuyển đổi tọa độ gốc sang tọa độ pixel màn hình
        const screenPoints = polyCoords
            .map(pt => `${(pt[0] * scaleX).toFixed(1)},${(pt[1] * scaleY).toFixed(1)}`)
            .join(' ');

        const polygon = document.createElementNS(svgNS, 'polygon');
        polygon.setAttribute('points', screenPoints);
        polygon.setAttribute('class', 'ocr-bbox-poly');
        polygon.setAttribute('data-line-id', String(item.id !== undefined ? item.id : index));

        // Hover events
        polygon.addEventListener('mouseenter', (e) => {
            highlightBbox(item.id !== undefined ? item.id : index);
            EventBus.emit('bbox:hover', { id: item.id !== undefined ? item.id : index, hover: true });

            if (tooltip) {
                const scorePercent = Math.round((item.score || 0) * 1000) / 10;
                const tooltipType = document.getElementById('tooltip-type');
                const tooltipScore = document.getElementById('tooltip-score');
                const tooltipText = document.getElementById('tooltip-text');

                if (tooltipType) tooltipType.textContent = item.type || 'Text';
                if (tooltipScore) tooltipScore.textContent = `${scorePercent}%`;
                if (tooltipText) tooltipText.textContent = item.text || '(Trống)';

                tooltip.classList.remove('d-none');
                updateTooltipPosition(e, tooltip);
            }
        });

        polygon.addEventListener('mousemove', (e) => {
            if (tooltip) {
                updateTooltipPosition(e, tooltip);
            }
        });

        polygon.addEventListener('mouseleave', () => {
            clearBboxHighlight();
            EventBus.emit('bbox:hover', { id: item.id !== undefined ? item.id : index, hover: false });
            if (tooltip) {
                tooltip.classList.add('d-none');
            }
        });

        polygon.addEventListener('click', () => {
            EventBus.emit('bbox:select', { id: item.id !== undefined ? item.id : index, item });
        });

        svg.appendChild(polygon);
    });

    overlayContainer.appendChild(svg);
}

/**
 * Cập nhật vị trí của Tooltip nổi theo vị trí con trỏ chuột
 * @param {MouseEvent} e
 * @param {HTMLElement} tooltip
 */
function updateTooltipPosition(e, tooltip) {
    const viewportRect = document.getElementById('viewport-container')?.getBoundingClientRect();
    if (!viewportRect) return;

    const x = e.clientX - viewportRect.left + 15;
    const y = e.clientY - viewportRect.top + 15;

    tooltip.style.left = `${Math.max(10, Math.min(x, viewportRect.width - 250))}px`;
    tooltip.style.top = `${Math.max(10, Math.min(y, viewportRect.height - 80))}px`;
}

/**
 * Làm sáng BBox cụ thể theo ID dòng
 * @param {number|string} lineId
 */
export function highlightBbox(lineId) {
    const polygons = document.querySelectorAll('.ocr-bbox-poly');
    polygons.forEach(p => {
        if (p.getAttribute('data-line-id') === String(lineId)) {
            p.classList.add('active');
        } else {
            p.classList.remove('active');
        }
    });
}

/**
 * Xóa toàn bộ trạng thái sáng của các BBox
 */
export function clearBboxHighlight() {
    const polygons = document.querySelectorAll('.ocr-bbox-poly.active');
    polygons.forEach(p => p.classList.remove('active'));
}

/**
 * Xóa hoàn toàn các BBox đang vẽ và ẩn Tooltip
 */
export function clearBboxOverlay() {
    const overlay = document.getElementById('bbox-overlay');
    if (overlay) overlay.innerHTML = '';
    const tooltip = document.getElementById('bbox-tooltip');
    if (tooltip) tooltip.classList.add('d-none');
}
