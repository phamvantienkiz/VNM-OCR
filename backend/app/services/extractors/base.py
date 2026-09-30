from abc import ABC, abstractmethod
from typing import Any, BinaryIO

from app.schemas.document import DocumentExtractionResponse

class BaseExtractor(ABC):
    """Base interface for all document extractors."""

    @abstractmethod
    def extract(self, file_input: BinaryIO | bytes, **kwargs: Any) -> DocumentExtractionResponse:
        """Extract document and return standardized response."""
        pass
