"""Unit tests for VietVocab tokenizer and decoder."""

from app.engine.vocab import VietVocab


def test_vocab_special_tokens():
    vocab = VietVocab()
    assert vocab.pad == 0
    assert vocab.go == 1
    assert vocab.eos == 2
    assert vocab.mask_token == 3
    assert vocab.i2c[0] == "<pad>"
    assert vocab.i2c[1] == "<sos>"
    assert vocab.i2c[2] == "<eos>"
    assert vocab.i2c[3] == "*"


def test_vocab_offset_is_four():
    vocab = VietVocab()
    # The first character in default chars is 'a'
    first_char = vocab.chars[0]
    assert vocab.c2i[first_char] == 4
    assert vocab.i2c[4] == first_char


def test_vocab_encode_decode():
    vocab = VietVocab()
    sample_text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    token_ids = vocab.encode(sample_text)

    # First token should be SOS (1) and last token EOS (2)
    assert token_ids[0] == 1
    assert token_ids[-1] == 2

    # Decoding should recover exact text
    decoded_text = vocab.decode(token_ids)
    assert decoded_text == sample_text


def test_vocab_batch_decode():
    vocab = VietVocab()
    samples = [
        "Độc lập - Tự do - Hạnh phúc",
        "Số: 123/QĐ-UBND",
        "Báo cáo tài chính năm 2026",
    ]
    token_batch = [vocab.encode(s) for s in samples]
    decoded_batch = vocab.batch_decode(token_batch)
    assert decoded_batch == samples


def test_vocab_unknown_characters_skipped():
    vocab = VietVocab()
    # Contains characters not in default vocab (e.g. emoji, Cyrillic)
    text_with_unknown = "Việt Nam 🇻🇳 và Москва"
    token_ids = vocab.encode(text_with_unknown)
    decoded = vocab.decode(token_ids)
    # Unknown characters skipped, known characters preserved
    assert "Việt Nam" in decoded
