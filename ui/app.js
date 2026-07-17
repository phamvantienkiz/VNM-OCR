// State variables
let currentFile = null;
let pdfDoc = null;
let currentPageNum = 1;
let pdfPagesData = []; // Array of { dataUrl: string, width: number, height: number, ocrResults: Array }
let imageOcrResults = null; // For single image upload
let currentOcrResults = null; // Active OCR result list for drawing

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const progressLabel = document.getElementById('progress-label');
const progressPercent = document.getElementById('progress-percent');
const progressBar = document.getElementById('progress-bar');
const resultSection = document.getElementById('result-section');

const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageIndicator = document.getElementById('page-indicator');
const runOcrBtn = document.getElementById('run-ocr-btn');
const copyTextBtn = document.getElementById('copy-text-btn');
const downloadTxtBtn = document.getElementById('download-txt-btn');

const previewImage = document.getElementById('preview-image');
const bboxOverlay = document.getElementById('bbox-overlay');
const imageWrapper = document.getElementById('image-wrapper');
const outputTextarea = document.getElementById('output-textarea');
const confidenceIndicator = document.getElementById('confidence-indicator');

// Setup Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('hover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('hover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('hover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    // File Input
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Toolbar Actions
    prevPageBtn.addEventListener('click', () => changePdfPage(-1));
    nextPageBtn.addEventListener('click', () => changePdfPage(1));
    runOcrBtn.addEventListener('click', executeOcr);
    
    copyTextBtn.addEventListener('click', copyTextToClipboard);
    downloadTxtBtn.addEventListener('click', downloadTextFile);

    // Responsive Bbox Redraw
    window.addEventListener('resize', () => {
        if (currentOcrResults) {
            drawBoundingBoxes(currentOcrResults);
        }
    });
});

// File Handling
function handleFileSelect(file) {
    currentFile = file;
    resetState();
    
    const fileType = file.type;
    
    if (fileType === 'application/pdf') {
        processPdf(file);
    } else if (fileType.startsWith('image/')) {
        processImage(file);
    } else {
        alert('Định dạng tệp không được hỗ trợ! Vui lòng chọn tệp PDF hoặc Hình ảnh.');
    }
}

function resetState() {
    pdfDoc = null;
    currentPageNum = 1;
    pdfPagesData = [];
    imageOcrResults = null;
    currentOcrResults = null;
    bboxOverlay.innerHTML = '';
    outputTextarea.value = '';
    confidenceIndicator.innerText = 'Độ chính xác: --';
    
    prevPageBtn.disabled = true;
    nextPageBtn.disabled = true;
    pageIndicator.innerText = 'Trang 1 / 1';
}

// Image Loader
function processImage(file) {
    showProgress('Đang tải ảnh...', 20);
    
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewImage.onload = () => {
            hideProgress();
            uploadSection.classList.add('hidden');
            resultSection.classList.remove('hidden');
            // Show page navigation controls only for PDFs
            prevPageBtn.classList.add('hidden');
            nextPageBtn.classList.add('hidden');
            pageIndicator.classList.add('hidden');
            
            // Adjust overlay
            bboxOverlay.innerHTML = '';
        };
    };
    reader.readAsDataURL(file);
}

// PDF Loader using PDF.js
async function processPdf(file) {
    showProgress('Đang phân tích tệp PDF...', 10);
    
    const fileReader = new FileReader();
    fileReader.onload = async function() {
        try {
            const typedarray = new Uint8Array(this.result);
            pdfDoc = await pdfjsLib.getDocument(typedarray).promise;
            
            const totalPages = Math.min(pdfDoc.numPages, 10); // Max 10 pages limit
            
            showProgress('Đang chuyển đổi PDF thành ảnh...', 30);
            
            for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
                showProgress(`Đang trích xuất trang ${pageNum}/${totalPages}...`, 30 + Math.round((pageNum / totalPages) * 60));
                
                const page = await pdfDoc.getPage(pageNum);
                const viewport = page.getViewport({ scale: 1.5 });
                
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                
                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;
                
                pdfPagesData.push({
                    dataUrl: canvas.toDataURL('image/jpeg', 0.9),
                    width: viewport.width,
                    height: viewport.height,
                    ocrResults: null
                });
            }
            
            hideProgress();
            uploadSection.classList.add('hidden');
            resultSection.classList.remove('hidden');
            
            // Show page navigation
            prevPageBtn.classList.remove('hidden');
            nextPageBtn.classList.remove('hidden');
            pageIndicator.classList.remove('hidden');
            
            displayPdfPage(1);
            
        } catch (error) {
            console.error(error);
            alert('Có lỗi xảy ra khi xử lý tệp PDF!');
            hideProgress();
        }
    };
    fileReader.readAsArrayBuffer(file);
}

function displayPdfPage(pageNum) {
    currentPageNum = pageNum;
    const pageData = pdfPagesData[pageNum - 1];
    
    previewImage.src = pageData.dataUrl;
    
    previewImage.onload = () => {
        // Render existing OCR results for this page if they exist
        if (pageData.ocrResults) {
            currentOcrResults = pageData.ocrResults;
            drawBoundingBoxes(currentOcrResults);
            updateTextResult(currentOcrResults);
        } else {
            currentOcrResults = null;
            bboxOverlay.innerHTML = '';
            outputTextarea.value = '';
            confidenceIndicator.innerText = 'Độ chính xác: --';
        }
    };

    // Update Indicators
    pageIndicator.innerText = `Trang ${pageNum} / ${pdfPagesData.length}`;
    prevPageBtn.disabled = pageNum === 1;
    nextPageBtn.disabled = pageNum === pdfPagesData.length;
}

function changePdfPage(direction) {
    const targetPage = currentPageNum + direction;
    if (targetPage >= 1 && targetPage <= pdfPagesData.length) {
        displayPdfPage(targetPage);
    }
}

// Progress Controls
function showProgress(message, percent) {
    uploadSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    progressLabel.innerText = message;
    progressPercent.innerText = `${percent}%`;
    progressBar.style.width = `${percent}%`;
}

function hideProgress() {
    progressSection.classList.add('hidden');
}

// OCR execution
async function executeOcr() {
    runOcrBtn.disabled = true;
    runOcrBtn.innerHTML = `
        <svg class="h-4 w-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89H18v3z" />
        </svg>
        Đang xử lý...
    `;
    outputTextarea.placeholder = 'Đang chạy mô hình AI nhận diện chữ...';
    
    try {
        let fileToSend = null;
        
        if (pdfDoc) {
            // Convert current PDF page canvas dataUrl back to a Blob file
            const dataUrl = pdfPagesData[currentPageNum - 1].dataUrl;
            const res = await fetch(dataUrl);
            const blob = await res.blob();
            fileToSend = new File([blob], `page_${currentPageNum}.jpg`, { type: 'image/jpeg' });
        } else {
            fileToSend = currentFile;
        }
        
        const formData = new FormData();
        formData.append('file', fileToSend);
        
        // POST to backend API
        const response = await fetch('/api/ocr', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }
        
        const results = await response.json();
        
        // Cache results
        if (pdfDoc) {
            pdfPagesData[currentPageNum - 1].ocrResults = results;
        } else {
            imageOcrResults = results;
        }
        
        currentOcrResults = results;
        drawBoundingBoxes(results);
        updateTextResult(results);
        
    } catch (error) {
        console.error(error);
        alert('Lỗi khi gửi yêu cầu OCR đến máy chủ! Hãy đảm bảo máy chủ backend đang chạy.');
        outputTextarea.placeholder = 'Không thể kết nối đến máy chủ nhận dạng OCR.';
    } finally {
        runOcrBtn.disabled = false;
        runOcrBtn.innerHTML = `
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Chạy OCR
        `;
    }
}

// UI Bounding Box Drawing & Scaling
function drawBoundingBoxes(results) {
    bboxOverlay.innerHTML = '';
    
    if (!results || results.length === 0) return;
    
    const imgWidth = previewImage.clientWidth;
    const imgHeight = previewImage.clientHeight;
    const naturalWidth = previewImage.naturalWidth;
    const naturalHeight = previewImage.naturalHeight;
    
    const scaleX = imgWidth / naturalWidth;
    const scaleY = imgHeight / naturalHeight;
    
    results.forEach((item, index) => {
        // item structure: [ [[x0, y0], [x1, y1], [x2, y2], [x3, y3]], [text, score] ]
        const points = item[0];
        const text = item[1][0];
        const score = item[1][1];
        
        // Find bounding rectangle corners
        const xs = points.map(p => p[0]);
        const ys = points.map(p => p[1]);
        const xMin = Math.min(...xs);
        const xMax = Math.max(...xs);
        const yMin = Math.min(...ys);
        const yMax = Math.max(...ys);
        
        // Compute scaled values
        const left = xMin * scaleX;
        const top = yMin * scaleY;
        const width = (xMax - xMin) * scaleX;
        const height = (yMax - yMin) * scaleY;
        
        // Create BBox div
        const bbox = document.createElement('div');
        bbox.className = 'bbox-box';
        bbox.style.left = `${left}px`;
        bbox.style.top = `${top}px`;
        bbox.style.width = `${width}px`;
        bbox.style.height = `${height}px`;
        bbox.setAttribute('tabindex', '0');
        bbox.setAttribute('aria-label', `Dòng chữ ${index + 1}: ${text}`);
        
        // Create Tooltip
        const tooltip = document.createElement('span');
        tooltip.className = 'bbox-tooltip';
        tooltip.innerText = `${text} (${Math.round(score * 100)}%)`;
        
        bbox.appendChild(tooltip);
        
        // Highlight corresponding text in output on hover
        bbox.addEventListener('mouseenter', () => highlightTextInEditor(index));
        bbox.addEventListener('mouseleave', clearTextHighlight);
        
        bboxOverlay.appendChild(bbox);
    });
}

function updateTextResult(results) {
    if (!results || results.length === 0) {
        outputTextarea.value = "Không phát hiện chữ viết nào trên trang.";
        confidenceIndicator.innerText = 'Độ chính xác: 0%';
        return;
    }
    
    // Extracted text strings
    const texts = results.map(item => item[1][0]);
    outputTextarea.value = texts.join('\n');
    
    // Average confidence score
    const scores = results.map(item => item[1][1]);
    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
    confidenceIndicator.innerText = `Độ chính xác: ${Math.round(avgScore * 100)}%`;
}

// BBox and Textbox Interactivity
function highlightTextInEditor(index) {
    const lines = outputTextarea.value.split('\n');
    if (index < lines.length) {
        // Highlight logic (placeholder or visual notification)
        outputTextarea.focus();
        
        // Find character offset
        let offset = 0;
        for (let i = 0; i < index; i++) {
            offset += lines[i].length + 1; // +1 for newline character
        }
        
        outputTextarea.setSelectionRange(offset, offset + lines[index].length);
    }
}

function clearTextHighlight() {
    // Clear selection
    outputTextarea.setSelectionRange(0, 0);
}

// Clipboard Copies
function copyTextToClipboard() {
    if (!outputTextarea.value) return;
    
    navigator.clipboard.writeText(outputTextarea.value).then(() => {
        const originalText = copyTextBtn.innerHTML;
        copyTextBtn.innerHTML = `
            <svg class="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Đã chép!
        `;
        setTimeout(() => {
            copyTextBtn.innerHTML = originalText;
        }, 1500);
    }).catch(err => {
        console.error('Không thể sao chép văn bản: ', err);
    });
}

// File Downloads
function downloadTextFile() {
    if (!outputTextarea.value) return;
    
    const element = document.createElement("a");
    const file = new Blob([outputTextarea.value], {type: 'text/plain;charset=utf-8'});
    element.href = URL.createObjectURL(file);
    
    const filename = pdfDoc ? 
        `${currentFile.name.replace('.pdf', '')}_page_${currentPageNum}.txt` : 
        `${currentFile.name.split('.')[0]}_ocr.txt`;
        
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}
