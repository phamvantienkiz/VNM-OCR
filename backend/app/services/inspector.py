"""Smart PDF Inspector Module.

Performs internal inspection of PDF binary streams to determine document characteristics
(Scanned, Born-Digital, Corrupted Vector, Complex Layout/Math) in < 5ms per page.
"""

from enum import Enum
import io
import re
from typing import BinaryIO, Any
from dataclasses import dataclass, field
import pdfplumber
from app.utils.image_utils import is_pdf_file


class PageType(str, Enum):
    """Classification of document / page nature."""

    DIGITAL_DOCUMENT = "DIGITAL_DOCUMENT"
    SCANNED_DOCUMENT = "SCANNED_DOCUMENT"
    CORRUPTED_VECTOR = "CORRUPTED_VECTOR"
    COMPLEX_DOCUMENT = "COMPLEX_DOCUMENT"


@dataclass
class PDFPageProfile:
    """Detailed structural profile of a single inspected PDF page."""

    page_num: int
    char_count: int
    raster_image_count: int
    scs_score: float  # Scanned Content Score [0.0 = Pure Digital, 1.0 = Pure Scan]
    has_math: bool = False
    has_complex_tables: bool = False
    page_type: PageType = PageType.DIGITAL_DOCUMENT
    metadata: dict[str, Any] = field(default_factory=dict)


class SmartPDFInspector:
    """Analyzes PDF page streams to classify documents without heavy neural network inference."""

    VERSION: str = "2.5.0"

    # Regex for Vietnamese diacritics
    VI_DIACRITICS_REGEX = re.compile(
        r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
        re.IGNORECASE,
    )

    # Unicode Private Use Area (PUA) indicating broken CMap / corrupted ToUnicode fonts
    PUA_REGEX = re.compile(r"[\uE000-\uF8FF]")

    # Unicode math symbols
    MATH_UNICODE_REGEX = re.compile(
        r"[\u2200-\u22FF\u2A00-\u2AFF\u2070-\u2079\u2080-\u2089\u2300-\u2335\U0001D400-\U0001D7FF]"
    )

    LATEX_MATH_FONT_PATTERNS = ["cmr", "cmmi", "cmsy", "msam", "msbm", "libertine", "cambriamath", "latinmodern"]

    @classmethod
    def analyze_page(cls, page: pdfplumber.page.Page, page_num: int = 1) -> PDFPageProfile:
        """Inspect a single pdfplumber Page object and compute its structural profile."""
        text = page.extract_text() or ""
        char_count = len(text.strip())
        images = page.images or []
        raster_count = len(images)

        # 1. Check for Corrupted Vector / Broken Fonts (PUA characters or unreadable gibberish)
        pua_matches = len(cls.PUA_REGEX.findall(text))
        is_corrupted = False
        if pua_matches > 5 or (char_count > 50 and pua_matches / char_count > 0.1):
            is_corrupted = True

        # 2. Compute Scanned Content Score (SCS)
        # Factors: presence of full-page raster image vs digital text density
        if raster_count > 0 and char_count < 30:
            scs_score = 1.0
        elif raster_count > 0 and char_count < 100:
            scs_score = 0.8
        elif char_count > 150 and raster_count == 0:
            scs_score = 0.0
        elif char_count > 50:
            scs_score = 0.15
        else:
            scs_score = 0.5

        # 3. Detect Math Formulas
        has_math = bool(cls.MATH_UNICODE_REGEX.search(text))

        # 4. Detect Complex Tables
        tables = page.extract_tables() or []
        has_complex_tables = len(tables) > 0

        # Classify PageType
        if is_corrupted:
            p_type = PageType.CORRUPTED_VECTOR
        elif scs_score >= 0.7:
            p_type = PageType.SCANNED_DOCUMENT
        elif has_math or has_complex_tables:
            p_type = PageType.COMPLEX_DOCUMENT
        else:
            p_type = PageType.DIGITAL_DOCUMENT

        return PDFPageProfile(
            page_num=page_num,
            char_count=char_count,
            raster_image_count=raster_count,
            scs_score=scs_score,
            has_math=has_math,
            has_complex_tables=has_complex_tables,
            page_type=p_type,
            metadata={"pua_matches": pua_matches},
        )

    @classmethod
    def inspect(cls, file_input: BinaryIO | bytes, sample_limit: int = 3) -> list[PDFPageProfile]:
        """Sample up to sample_limit pages (first, middle, last) and evaluate document profile."""
        if hasattr(file_input, "read"):
            file_input.seek(0)
            file_obj = file_input
        else:
            file_obj = io.BytesIO(file_input)

        profiles: list[PDFPageProfile] = []
        with pdfplumber.open(file_obj) as pdf:
            total_pages = len(pdf.pages)
            if total_pages == 0:
                return profiles

            if total_pages <= sample_limit:
                indices = list(range(total_pages))
            else:
                indices = [0, total_pages // 2, total_pages - 1]

            for idx in indices:
                page = pdf.pages[idx]
                profile = cls.analyze_page(page, page_num=idx + 1)
                profiles.append(profile)

        if hasattr(file_input, "seek"):
            file_input.seek(0)

        return profiles

    @classmethod
    def classify_document(cls, profiles: list[PDFPageProfile]) -> PageType:
        """Aggregate sampled page profiles to form an overall document classification."""
        if not profiles:
            return PageType.SCANNED_DOCUMENT

        # If any sample is corrupted vector, treat whole document as corrupted vector
        if any(p.page_type == PageType.CORRUPTED_VECTOR for p in profiles):
            return PageType.CORRUPTED_VECTOR

        # Average SCS score
        avg_scs = sum(p.scs_score for p in profiles) / len(profiles)

        if avg_scs >= 0.6:
            return PageType.SCANNED_DOCUMENT
        elif any(p.page_type == PageType.COMPLEX_DOCUMENT for p in profiles):
            return PageType.COMPLEX_DOCUMENT
        elif avg_scs <= 0.2:
            return PageType.DIGITAL_DOCUMENT
        else:
            return PageType.SCANNED_DOCUMENT
