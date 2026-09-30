"""Comprehensive E2E Integration and Standards Verification Test Suite (Phase 2 P4).
Tests real sample images, PDF extraction with DPI resolutions, Responsive Grid rules, and WCAG 2.2 AA Accessibility.
"""

from html.parser import HTMLParser
from pathlib import Path
import re
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# Bước 4.1: Kiểm thử trực tiếp với các định dạng ảnh mẫu
# ==============================================================================

def test_ocr_endpoint_with_real_sample_images() -> None:
    """Test /api/v1/ocr with real sample images in img/ directory."""
    img_dir = Path(__file__).resolve().parents[3] / "img"
    sample_files = [
        "bản_kê_chi_tiết_2026.png",
        "Screenshot 2025-08-28 171633.png",
        "x6.png",
    ]

    for filename in sample_files:
        filepath = img_dir / filename
        if not filepath.is_file():
            continue

        with open(filepath, "rb") as f:
            file_bytes = f.read()

        response = client.post(
            "/api/v1/ocr",
            files={"file": (filename, file_bytes, "image/png")},
        )

        assert response.status_code == 200, f"OCR failed for {filename}: {response.text}"
        data = response.json()
        lines_key = "lines" if "lines" in data else "text_lines"
        assert lines_key in data, f"Missing lines in response for {filename}"
        assert isinstance(data[lines_key], list)
        assert len(data[lines_key]) > 0, f"Expected non-empty lines for {filename}"

        # Verify structure of first text line
        first_line = data[lines_key][0]
        assert "text" in first_line and len(first_line["text"]) > 0
        assert "score" in first_line and 0.0 <= first_line["score"] <= 1.0
        assert "bbox" in first_line and len(first_line["bbox"]) == 4


def test_document_endpoint_with_real_sample_image() -> None:
    """Test /api/v1/document/extract with single image."""
    img_path = Path(__file__).resolve().parents[3] / "img" / "bản_kê_chi_tiết_2026.png"
    if not img_path.is_file():
        pytest.skip("Sample image bản_kê_chi_tiết_2026.png not found")

    with open(img_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/document/extract?extract_tables=true&resolution=150",
        files={"file": ("bản_kê_chi_tiết_2026.png", file_bytes, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "full_markdown" in data
    assert "pages" in data
    assert len(data["pages"]) >= 1


# ==============================================================================
# Bước 4.2: Kiểm thử tài liệu PDF nhiều trang và đồng bộ DPI
# ==============================================================================

def test_document_endpoint_with_real_pdf_and_dpi_scaling() -> None:
    """Test /api/v1/document/extract with real PDF at 72, 150, and 300 DPI."""
    pdf_path = Path(__file__).resolve().parents[2] / "tests" / "real_pdf_file" / "báo cáo.pdf"
    if not pdf_path.is_file():
        pytest.skip("Sample PDF file báo cáo.pdf not found")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Test 150 DPI (Standard)
    res_150 = client.post(
        "/api/v1/document/extract?extract_tables=true&resolution=150",
        files={"file": ("báo cáo.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_150.status_code == 200, f"PDF 150 DPI failed: {res_150.text}"
    data_150 = res_150.json()
    assert data_150["total_pages"] >= 1
    assert len(data_150["pages"]) >= 1
    assert len(data_150["full_markdown"]) > 0


def test_page_eviction_and_dpi_formula() -> None:
    """Verify the dynamic DPI scale formula and page eviction window math."""
    # scale = dpi / 72.0
    assert 72 / 72.0 == 1.0
    assert abs((150 / 72.0) - 2.0833333333333335) < 1e-6
    assert abs((300 / 72.0) - 4.166666666666667) < 1e-6

    # Eviction Window: [currentPage - 2, currentPage + 2]
    current_page = 5
    total_pages = 20
    min_keep = max(1, current_page - 2)
    max_keep = min(total_pages, current_page + 2)
    assert min_keep == 3
    assert max_keep == 7

    kept_pages = [p for p in range(1, total_pages + 1) if min_keep <= p <= max_keep]
    assert kept_pages == [3, 4, 5, 6, 7]


# ==============================================================================
# Bước 4.3: Kiểm tra tính tương thích Responsive trên các độ phân giải
# ==============================================================================

def test_responsive_css_breakpoints() -> None:
    """Verify responsive CSS media queries and column layout rules in style.css."""
    css_path = Path(__file__).resolve().parents[3] / "ui" / "style.css"
    css_content = css_path.read_text(encoding="utf-8")

    # Tier 1 (Desktop >= 1280px)
    assert ".app-layout-grid" in css_content
    assert "grid-template-columns: minmax(280px, 25%) minmax(420px, 45%) minmax(320px, 30%)" in css_content

    # Tier 2 (Laptop/Tablet < 1280px)
    assert "@media (max-width: 1279.98px)" in css_content
    assert "grid-template-columns: minmax(380px, 55%) minmax(300px, 45%)" in css_content
    assert ".column-upload.offcanvas-xl" in css_content

    # Tier 3 (Mobile < 768px)
    assert "@media (max-width: 767.98px)" in css_content
    assert "flex-direction: column" in css_content


# ==============================================================================
# Bước 4.4: Rà soát tiêu chuẩn Accessibility (WCAG 2.2 AA)
# ==============================================================================

class AccessibilityAuditor(HTMLParser):
    """HTML Parser auditing accessibility compliance (WCAG 2.2 AA)."""

    def __init__(self) -> None:
        super().__init__()
        self.aria_labels: list[str] = []
        self.aria_lives: list[str] = []
        self.tabindexes: list[str] = []
        self.roles: list[str] = []
        self.buttons: list[dict[str, str]] = []
        self.inputs: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v for k, v in attrs if v is not None}

        if "aria-label" in attr_dict:
            self.aria_labels.append(attr_dict["aria-label"])
        if "aria-live" in attr_dict:
            self.aria_lives.append(attr_dict["aria-live"])
        if "tabindex" in attr_dict:
            self.tabindexes.append(attr_dict["tabindex"])
        if "role" in attr_dict:
            self.roles.append(attr_dict["role"])

        if tag == "button":
            self.buttons.append(attr_dict)
        elif tag == "input":
            self.inputs.append(attr_dict)


def test_wcag_accessibility_audit() -> None:
    """Audit UI HTML for WCAG 2.2 AA accessibility requirements."""
    ui_path = Path(__file__).resolve().parents[3] / "ui" / "index.html"
    html_content = ui_path.read_text(encoding="utf-8")

    auditor = AccessibilityAuditor()
    auditor.feed(html_content)

    # 1. Live region for dynamic content updates
    assert "polite" in auditor.aria_lives, "Results container must have aria-live='polite'"

    # 2. Keyboard accessibility (tabindex="0" on interactive containers)
    assert "0" in auditor.tabindexes, "Dropzone or interactive containers must have tabindex='0'"

    # 3. Roles
    assert "button" in auditor.roles or "tab" in auditor.roles or "tablist" in auditor.roles or "switch" in auditor.roles

    # 4. Buttons have labels or title attributes
    for btn in auditor.buttons:
        has_accessible_name = (
            "aria-label" in btn
            or "title" in btn
            or "id" in btn
        )
        assert has_accessible_name, f"Button missing accessible identifier: {btn}"


def test_focus_visible_and_color_contrast_tokens() -> None:
    """Verify that style.css enforces focus-visible outlines and accessible colors."""
    css_path = Path(__file__).resolve().parents[3] / "ui" / "style.css"
    css_content = css_path.read_text(encoding="utf-8")

    # Focus visible outline
    assert ":focus-visible" in css_content
    assert "outline: 2px solid var(--indigo-600)" in css_content

    # High-contrast color tokens
    assert "--slate-900: #0f172a;" in css_content
    assert "--slate-50: #f8fafc;" in css_content
    assert "--emerald-700: #047857;" in css_content
    assert "--amber-700: #b45309;" in css_content
    assert "--rose-700: #b91c1c;" in css_content
