"""Tests for UI DOM Structure and CSS Grid Layout (Phase 2 P1 & P2)."""

from html.parser import HTMLParser
from pathlib import Path
import pytest


class DomIdCollector(HTMLParser):
    """Simple HTMLParser that collects all tag IDs and attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.elements_by_id: dict[str, dict[str, str]] = {}
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v for k, v in attrs if v is not None}
        if "id" in attr_dict:
            element_id = attr_dict["id"]
            self.ids.add(element_id)
            self.elements_by_id[element_id] = attr_dict
        if tag == "a" and "href" in attr_dict:
            self.links.append(attr_dict)


@pytest.fixture
def ui_html_content() -> str:
    """Read ui/index.html content."""
    ui_path = Path(__file__).resolve().parents[3] / "ui" / "index.html"
    assert ui_path.is_file(), f"ui/index.html not found at {ui_path}"
    return ui_path.read_text(encoding="utf-8")


@pytest.fixture
def dom_collector(ui_html_content: str) -> DomIdCollector:
    """Parse ui/index.html with DomIdCollector."""
    parser = DomIdCollector()
    parser.feed(ui_html_content)
    return parser


@pytest.fixture
def ui_css_content() -> str:
    """Read ui/style.css content."""
    css_path = Path(__file__).resolve().parents[3] / "ui" / "style.css"
    assert css_path.is_file(), f"ui/style.css not found at {css_path}"
    return css_path.read_text(encoding="utf-8")


def test_topbar_elements(dom_collector: DomIdCollector) -> None:
    """Test Topbar Header and Health Badge elements (Bước 1.2)."""
    assert "api-status" in dom_collector.ids
    api_status_classes = dom_collector.elements_by_id["api-status"].get("class", "")
    assert "status-badge" in api_status_classes

    # Link to /docs Swagger
    doc_links = [link for link in dom_collector.links if link.get("href") == "/docs"]
    assert len(doc_links) > 0, "Missing link to /docs Swagger"


def test_column_1_upload_and_config_elements(dom_collector: DomIdCollector) -> None:
    """Test Column 1 (Upload & Config) elements (Bước 2.1)."""
    # Dropzone & File Input
    assert "drop-zone" in dom_collector.ids
    assert "file-input" in dom_collector.ids
    assert "file-info-card" in dom_collector.ids
    assert "change-file-btn" in dom_collector.ids

    # Endpoints & Mode Switchers
    assert "mode-ocr" in dom_collector.ids
    assert "mode-doc" in dom_collector.ids
    assert "document-options-group" in dom_collector.ids

    # Resolution & TSR options
    assert "dpi-72" in dom_collector.ids
    assert "dpi-150" in dom_collector.ids
    assert "dpi-300" in dom_collector.ids
    assert "extract-tables-checkbox" in dom_collector.ids

    # Confidence Threshold Slider
    assert "confidence-slider" in dom_collector.ids
    slider_attrs = dom_collector.elements_by_id["confidence-slider"]
    assert slider_attrs.get("min") == "0.50", "Confidence slider min should be 0.50"
    assert slider_attrs.get("max") == "1.00", "Confidence slider max should be 1.00"
    assert "confidence-value" in dom_collector.ids

    # Action buttons
    assert "run-ocr-btn" in dom_collector.ids
    assert "reset-btn" in dom_collector.ids

    # PDF Thumbnails
    assert "pdf-thumbnails-container" in dom_collector.ids
    assert "pdf-thumbnails-list" in dom_collector.ids


def test_column_2_viewer_elements(dom_collector: DomIdCollector) -> None:
    """Test Column 2 (Viewer & Visualizer) elements (Bước 2.2)."""
    # Zoom toolbar
    assert "zoom-out-btn" in dom_collector.ids
    assert "zoom-reset-btn" in dom_collector.ids
    assert "zoom-in-btn" in dom_collector.ids
    assert "zoom-fit-btn" in dom_collector.ids
    assert "zoom-ratio-badge" in dom_collector.ids

    # PDF Nav & Toggle BBox
    assert "viewer-pdf-nav" in dom_collector.ids
    assert "prev-page-btn" in dom_collector.ids
    assert "next-page-btn" in dom_collector.ids
    assert "toggle-bbox-btn" in dom_collector.ids

    # Viewport & Canvas Wrapper
    assert "viewport-container" in dom_collector.ids
    assert "viewport-empty-state" in dom_collector.ids
    assert "pan-zoom-container" in dom_collector.ids
    assert "preview-image" in dom_collector.ids
    assert "pdf-render-canvas" in dom_collector.ids
    assert "bbox-overlay" in dom_collector.ids
    assert "bbox-tooltip" in dom_collector.ids


def test_column_3_results_elements(dom_collector: DomIdCollector) -> None:
    """Test Column 3 (Results & Actions) elements (Bước 2.3)."""
    # Metrics
    assert "metric-time" in dom_collector.ids
    assert "metric-lines" in dom_collector.ids
    assert "metric-confidence" in dom_collector.ids

    # Tabs
    assert "tab-markdown" in dom_collector.ids
    assert "tab-lines" in dom_collector.ids
    assert "tab-json" in dom_collector.ids

    # Tab Content Panes & Accessibility aria-live
    assert "resultTabsContent" in dom_collector.ids
    tabs_content = dom_collector.elements_by_id["resultTabsContent"]
    assert tabs_content.get("aria-live") == "polite"

    assert "pane-markdown" in dom_collector.ids
    assert "output-markdown-textarea" in dom_collector.ids
    assert "pane-lines" in dom_collector.ids
    assert "lines-list-container" in dom_collector.ids
    assert "pane-json" in dom_collector.ids
    assert "output-json-view" in dom_collector.ids

    # Export toolbar
    assert "copy-text-btn" in dom_collector.ids
    assert "download-txt-btn" in dom_collector.ids
    assert "download-json-btn" in dom_collector.ids


def test_css_grid_and_design_tokens(ui_css_content: str) -> None:
    """Test CSS Grid layout and design tokens in ui/style.css (Bước 1.4)."""
    assert ".app-layout-grid" in ui_css_content
    assert "grid-template-columns:" in ui_css_content
    assert "--indigo-600:" in ui_css_content
    assert "--slate-900:" in ui_css_content
    assert "@media (max-width: 1279.98px)" in ui_css_content
    assert "@media (max-width: 767.98px)" in ui_css_content


def test_js_modules_static_serving() -> None:
    """Test that all modular JS files exist and are served via FastAPI static mount."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)

    js_files = [
        "js/state.js",
        "js/api.js",
        "js/pdf-loader.js",
        "js/bbox-renderer.js",
        "js/app.js",
    ]

    for js_file in js_files:
        res = client.get(f"/ui/{js_file}")
        assert res.status_code == 200, f"Failed to serve /ui/{js_file}"
        assert len(res.text) > 0, f"/ui/{js_file} is empty"


def test_js_modules_content_and_exports() -> None:
    """Test that JS modules export the required functions defined in Phase 2 P3 plan."""
    ui_dir = Path(__file__).resolve().parents[3] / "ui" / "js"

    # 1. state.js
    state_js = (ui_dir / "state.js").read_text(encoding="utf-8")
    assert "export const AppState" in state_js
    assert "export const EventBus" in state_js
    assert "export function updateFilteredLinesAndMetrics" in state_js
    assert "export function buildPageCacheKey" in state_js

    # 2. api.js
    api_js = (ui_dir / "api.js").read_text(encoding="utf-8")
    assert "export async function checkHealth" in api_js
    assert "export async function startHealthPolling" in api_js
    assert "export function stopHealthPolling" in api_js
    assert "export function abortCurrentRequest" in api_js
    assert "export async function sendOcrRequest" in api_js
    assert "export async function sendDocumentRequest" in api_js
    assert "export function sanitizeHtml" in api_js

    # 3. pdf-loader.js
    pdf_js = (ui_dir / "pdf-loader.js").read_text(encoding="utf-8")
    assert "export function dpiToScale" in pdf_js
    assert "export async function loadPdfDocument" in pdf_js
    assert "export async function renderPdfPageToCanvas" in pdf_js
    assert "export async function exportPdfPageToBlob" in pdf_js
    assert "export async function renderPdfThumbnail" in pdf_js
    assert "export function evictDistantPages" in pdf_js

    # 4. bbox-renderer.js
    bbox_js = (ui_dir / "bbox-renderer.js").read_text(encoding="utf-8")
    assert "export function normalizeBbox" in bbox_js
    assert "export function renderBoundingBoxes" in bbox_js
    assert "export function highlightBbox" in bbox_js
    assert "export function clearBboxHighlight" in bbox_js
    assert "export function clearBboxOverlay" in bbox_js
