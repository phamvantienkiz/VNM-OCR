"""Global Constants and Model Labels."""

# Required ONNX model weight files
REQUIRED_MODEL_FILES = [
    "det.onnx",
    "cnn.onnx",
    "encoder.onnx",
    "decoder.onnx",
    "layout.onnx",
    "tsr.onnx",
]

# YOLOv10 Document Layout Analysis Labels (Verified directly from layout.onnx metadata)
LAYOUT_LABELS = [
    "title",            # 0
    "text",             # 1 ('plain text')
    "reference",        # 2 ('abandon' - headers/footers/references)
    "figure",           # 3
    "figure_caption",   # 4
    "table",            # 5
    "table_caption",    # 6
    "table_footnote",   # 7 (Verified: table footnote)
    "equation",         # 8 ('isolate_formula')
    "figure_caption",   # 9 ('formula_caption' / caption)
]

# Raw names map from ONNX metadata for exact reference
LAYOUT_ONNX_NAMES = {
    0: "title",
    1: "plain text",
    2: "abandon",
    3: "figure",
    4: "figure_caption",
    5: "table",
    6: "table_caption",
    7: "table_footnote",
    8: "isolate_formula",
    9: "formula_caption",
}

# YOLOv10 Table Structure Recognition Labels
TSR_LABELS = [
    "table",
    "table column",
    "table row",
    "table column header",
    "table projected row header",
    "table spanning cell",
]

# Special tokens for VietOCR autoregressive decoder
TOKEN_PAD = 0
TOKEN_SOS = 1
TOKEN_EOS = 2
TOKEN_MASK = 3
TOKEN_OFFSET = 4  # Characters start at index 4

# Image processing defaults
DEFAULT_DET_MAX_SIDE = 960
DEFAULT_REC_IMAGE_HEIGHT = 32
DEFAULT_DROP_SCORE = 0.5
DEFAULT_LAYOUT_THRESHOLD = 0.5
DEFAULT_TSR_THRESHOLD = 0.2
