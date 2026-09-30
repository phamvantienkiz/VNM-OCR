"""Vietnamese OCR Vocabulary Tokenizer and Decoder.

This module provides a standalone token-to-character and character-to-token
mapping for VietOCR Seq2Seq/Transformer models without requiring PyTorch.
Follows the exact token indexing standard:
  - 0: <pad>
  - 1: <sos> / <go>
  - 2: <eos>
  - 3: * (mask token)
  - 4+: Real character tokens (offset +4)
"""

from typing import Sequence


class VietVocab:
    """Standalone VietOCR Vocabulary Tokenizer and Decoder."""

    DEFAULT_CHARS: str = (
        "aAàÀảẢãÃáÁạẠăĂằẰẳẲẵẴắẮặẶâÂầẦẩẨẫẪấẤậẬbBcCdDđĐeEèÈẻẺẽẼéÉẹẸêÊềỀểỂễỄếẾệỆ"
        "fFgGhHiIìÌỉỈĩĨíÍịỊjJkKlLmMnNoOòÒỏỎõÕóÓọỌôÔồỒổỔỗỖốỐộỘơƠờỜởỞỡỠớỚợỢpPqQrRsStTuUùÙủỦũŨúÚụỤưƯừỪửỬữỮứỨựỰ"
        "vVwWxXyYỳỲỷỶỹỸýÝỵỴzZ0123456789!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
    )

    def __init__(self, chars: str | None = None) -> None:
        self.pad: int = 0
        self.go: int = 1
        self.eos: int = 2
        self.mask_token: int = 3

        self.chars: str = chars if chars is not None else self.DEFAULT_CHARS

        # Offset is strictly +4 to match VietOCR weights
        self.c2i: dict[str, int] = {c: i + 4 for i, c in enumerate(self.chars)}
        self.i2c: dict[int, str] = {i + 4: c for i, c in enumerate(self.chars)}

        self.i2c[0] = "<pad>"
        self.i2c[1] = "<sos>"
        self.i2c[2] = "<eos>"
        self.i2c[3] = "*"

    def encode(self, text: str) -> list[int]:
        """Encode text string into token IDs.

        Note:
            Characters not present in vocabulary are safely skipped
            (unlike original VietOCR which raises KeyError) to avoid crashing OCR pipelines.
        """
        return [self.go] + [self.c2i[c] for c in text if c in self.c2i] + [self.eos]

    def decode(self, token_ids: Sequence[int]) -> str:
        """Decode a sequence of token IDs back into Unicode UTF-8 string."""
        first = 1 if self.go in token_ids else 0
        last = list(token_ids).index(self.eos) if self.eos in token_ids else len(token_ids)

        valid_ids = list(token_ids)[first:last]
        # Ignore special tokens pad (0), sos (1), mask (3)
        res = [self.i2c[i] for i in valid_ids if i in self.i2c and i >= 4]
        return "".join(res)

    def batch_decode(self, token_arrays: Sequence[Sequence[int]]) -> list[str]:
        """Decode a batch of token sequences."""
        return [self.decode(ids) for ids in token_arrays]

    def __len__(self) -> int:
        return len(self.c2i) + 4

    def __str__(self) -> str:
        return self.chars
