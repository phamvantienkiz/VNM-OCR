"""Tests for Document Extractors (Base, Native, VNM, Docling, Paddle)."""

import pytest
from unittest.mock import MagicMock
from app.exceptions.custom import ExtractorNotAvailableError
from app.schemas.document import DocumentExtractionResponse
from app.services.extractors.base import BaseExtractor
from app.services.extractors.native import NativePDFExtractor
from app.services.extractors.vnm import VNMOCRExtractor
from app.services.extractors.docling import DoclingUniversalExtractor
from app.services.extractors.paddle import PaddleOCRExtractor


def test_base_extractor_attributes():
    native = NativePDFExtractor()
    assert isinstance(native, BaseExtractor)
    assert native.name == "native_pdf"
    assert native.requires_image_input is False
    assert ".pdf" in native.supported_extensions

    docling = DoclingUniversalExtractor()
    assert isinstance(docling, BaseExtractor)
    assert docling.name == "docling_universal"
    assert docling.requires_image_input is False
    assert ".docx" in docling.supported_extensions

    paddle = PaddleOCRExtractor()
    assert isinstance(paddle, BaseExtractor)
    assert paddle.name == "paddle_ocr"
    assert paddle.requires_image_input is True
    assert ".pdf" in paddle.supported_extensions

    mock_engine = MagicMock()
    vnm = VNMOCRExtractor(engine_manager=mock_engine)
    assert isinstance(vnm, BaseExtractor)
    assert vnm.name == "vnm_ocr"
    assert vnm.requires_image_input is True
    assert ".pdf" in vnm.supported_extensions


def test_docling_not_available_raises():
    docling = DoclingUniversalExtractor()
    # In test environment without docling installed, calling extract should raise ExtractorNotAvailableError
    with pytest.raises(ExtractorNotAvailableError) as exc_info:
        docling.extract(b"dummy docx bytes", filename="test.docx")
    assert exc_info.value.status_code == 501
    assert "DoclingUniversalExtractor" in exc_info.value.message


def test_paddle_not_available_raises():
    paddle = PaddleOCRExtractor()
    # In test environment without paddleocr installed, calling extract should raise ExtractorNotAvailableError
    with pytest.raises(ExtractorNotAvailableError) as exc_info:
        paddle.extract(b"dummy pdf bytes")
    assert exc_info.value.status_code == 501
    assert "PaddleOCRExtractor" in exc_info.value.message


def test_vnm_extractor_delegates_to_document_service():
    mock_engine = MagicMock()
    vnm = VNMOCRExtractor(engine_manager=mock_engine)

    # Mock _document_service.extract_document
    fake_response = DocumentExtractionResponse(
        total_pages=1,
        full_markdown="# Test Title\nTest Body",
        pages=[],
        elapsed_ms=10.0,
    )
    vnm._document_service.extract_document = MagicMock(return_value=fake_response)

    result = vnm.extract(b"test file content", extract_tables=True, resolution=150, is_vector_recovery=True)

    vnm._document_service.extract_document.assert_called_once_with(
        file_input=b"test file content",
        extract_tables=True,
        resolution=150,
    )
    assert result.metadata is not None
    assert result.metadata.pipeline_used == "vnm_ocr"
    assert result.metadata.requires_image_input is True
    assert result.metadata.is_vector_recovery is True
