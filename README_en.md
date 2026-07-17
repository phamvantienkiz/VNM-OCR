<p align="center">
  <a href="./README.md">Tiếng Việt</a> |
  <a href="./README_en.md">English</a> |
</p>

# *Deep*Doc + VietOCR - Fast and Cost-effective OCR Tool for Vietnamese

- [1. Introduction](#1)
- [2. Architecture](#2)
- [3. Installation & Running](#3)
- [4. Repository Origin & License](#4)

<a name="1"></a>

## 1. Introduction

With a wide range of documents from various sources and formats, along with diverse retrieval requirements, an accurate extraction tool is essential for any business. Today, we introduce DeepDoc, a very fast and cost-efficient OCR tool that only requires running on a CPU. In addition, it also comes with Layout Recognizer and Table Structure Recognizer features, which help preserve the document's formatting after OCR.

However, DeepDoc has not yet been standardized for Vietnamese, so we replaced the Text Recognizer with VietOCR and its ONNX version to achieve better Vietnamese text recognition.

You can also check out the original version of DeepDoc [here](https://github.com/infiniflow/ragflow/blob/main/deepdoc/README.md). Since DeepDoc is essentially a data processing component for the RAG pipeline in the RAGFlow project, separating it into an independent Git repository makes customizing the application much more convenient.

<a name="2"></a>

## 2. Architecture

### 2.1 OCR

In this part, DeepDoc uses PaddleOCR - a very popular open-source tool developed by Baidu - after converting it into ONNX. ONNX (Open Neural Network Exchange) is an open format for AI models, allowing export and import of models between multiple frameworks (PyTorch, TensorFlow, etc.). It enables cross-platform compatibility, optimizes inference speed on CPU/GPU, and reduces infrastructure costs when deployed.

The OCR PP-OCRv5 architecture includes four main components:

- **Image Preprocessing Module**: Enhances image quality, handles rotation/skew using orientation classification (PP-LCNet) and unwarping (UVDoc).
- **Text Detection**: Upgraded from PP-OCRv4 with backbone PP-HGNetV2, knowledge distillation from GOT-OCR2.0, and data augmentation. Retains PFHead and DSR from the previous version.
- **Text Line Orientation Classification**: Automatically detects and corrects text line orientation (flipped, rotated) to prepare for recognition.
- **Text Recognition**: Two-branch architecture with PP-HGNetV2, trained with GTC-NRTR (attention-based) to guide SVTR-HGNet (CTC, lightweight, fast).

For more details about PP-OCRv5, you can refer to the official documentation [here](https://arxiv.org/html/2507.05595v1).

The Recognition module of Paddle has been replaced with VietOCR and its ONNX version to achieve more accurate Vietnamese text recognition. You can explore more about VietOCR [here](https://github.com/pbcquoc/vietocr). For the process of converting VietOCR into the ONNX format, we referred to [this article](https://viblo.asia/p/chuyen-doi-mo-hinh-hoc-sau-ve-onnx-bWrZnz4vZxw).

### 2.2 Layout Recognizer & Table Structure Recognizer

In this part, DeepDoc uses YOLOv10 (You Only Look Once) in its ONNX version.
The basic architecture consists of three main components:

- **Backbone**: Extracts features from the image, using a lightweight and efficient design.
- **Neck**: Combines multi-scale features (an improved FPN/PAN) to detect both small and large objects effectively.
- **Head**: Uses an anchor-free decoupled head (separating classification and regression branches), which improves accuracy and makes training easier.

In DeepDoc, YOLOv10 is trained to recognize label types for both Layout Recognizer and Table Structure Recognizer:

- **Layout Recognizer (10 categories)**: Text, Title, Image, Image Caption, Table, Table Caption, Header, Footer, Reference, Equation.
- **Table Structure Recognition (5 types)**: Column, Row, Column header, Projected row header, Spanning cell.

To understand more about YOLOv10, you can refer to the official documentation [here](https://arxiv.org/pdf/2405.14458).

<a name="3"></a>

## 3. Installation and Testing

### 3.1. Environment Setup

First, clone the git repository:

```bash
git clone https://github.com/hoaivannguyen/deepdoc_vietocr.git
cd deepdoc_vietocr
```

Create and activate a virtual environment to manage dependencies independently:

```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### 3.2. Command Line Interface (CLI)

#### Run OCR Text Recognition:

```bash
python t_ocr.py --inputs=path_to_images_or_pdfs --output_dir=path_to_store_result
```

_The input can be a directory containing images or PDFs, or a file path to a single image or PDF. The output will include 1 image with the detected bounding boxes and 1 text file containing the OCR text._

#### Run Layout & Table Structure Recognition:

```bash
# Layout Recognizer
python t_recognizer.py --inputs=path_to_images_or_pdfs --threshold=0.2 --mode=layout --output_dir=path_to_store_result

# Table Structure Recognizer (TSR)
python t_recognizer.py --inputs=path_to_images_or_pdfs --threshold=0.2 --mode=tsr --output_dir=path_to_store_result
```

### 3.3. Visual Testing Web UI

To test the OCR module interactively on a Web Dashboard, run the built-in API demo server:

```bash
python server.py
```

Then access **`http://127.0.0.1:8000/`** in your web browser. You can drag and drop images or PDF files to run OCR and visually inspect bounding box text coordinates upon hovering.

<a name="4"></a>

## 4. Repository Origin & License

### 4.1. Repository Origin & Acknowledgements

This project is a deeply improved version, structurally optimized and extensively extended based on the following source repository:

- **deepdoc_vietocr** (developed by [hoaivannguyen](https://github.com/hoaivannguyen/deepdoc_vietocr)).

The system inherits and integrates core technical components from the following well-known open-source projects:

1. **DeepDoc / RAGFlow** (developed by [InfiniFlow](https://github.com/infiniflow/ragflow) under the _Apache 2.0_ license): Provides layout processing, table recognition, and PDF parsing capabilities.
2. **VietOCR** (developed by [pbcquoc](https://github.com/pbcquoc/vietocr) under the _Apache 2.0_ license): Provides the optical character recognition (OCR) library and model for the Vietnamese language.

_We would like to express our sincere respect and gratitude to the authors and communities that developed the original projects above._

### 4.2. Copyright License & Non-Commercial Restriction

To protect the contributions of the community and the intellectual effort of the development team, this project is released under a **Non-Commercial Restricted Open Source License**, with the following terms:

#### A. Source Code

The source code of this project is governed by **Apache License 2.0 with an additional Commons Clause restriction**:

- **Preserve the original copyright:** All copyright information and author headers at the beginning of each source code file inherited from Ragflow/DeepDoc and VietOCR must be kept intact.
- **Rights to modify and share:** You are permitted to view, copy, modify, and redistribute this source code for learning, teaching, academic research, or internal non-profit use.
- **COMMERCIAL USE PROHIBITED (Commons Clause):** It is strictly prohibited to use, copy, modify, or distribute this source code, including any derivative modifications, for any commercial purpose in any form. This includes, but is not limited to, selling software, packaging it as a proprietary commercial product, or using it to provide a paid cloud service (commercial SaaS/API).

#### B. Model Weights

All model weight files (Model Weights/Checkpoints) fine-tuned and released by this project are strictly licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.

- You must provide attribution to this project and the original authors when using the model.
- You may not use this model for any commercial activity or revenue-generating purpose.
- If you further fine-tune or improve a model derived from our weights, you must share the results under the same non-commercial license (ShareAlike).

#### C. Disclaimer

Unless required by applicable law or agreed to in writing, the software and models are distributed on an **"AS IS"** basis, **WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND**, whether express or implied, including but not limited to performance or accuracy.

_See [LICENSE](LICENSE) for details._

---

## References

- RAGFlow GitHub: https://github.com/infiniflow/ragflow
- PP-OCRv5: https://arxiv.org/html/2507.05595v1
- VietOCR GitHub: https://github.com/pbcquoc/vietocr
- VietOCR ONNX: https://viblo.asia/p/chuyen-doi-mo-hinh-hoc-sau-ve-onnx-bWrZnz4vZxw
- YOLOv10: https://arxiv.org/pdf/2405.14458
