"""Real-world sample validation script."""

import sys
from pathlib import Path
import cv2
import numpy as np

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.engine.manager import EngineManager
from app.services.document_service import DocumentService


def main():
    backend_dir = Path(__file__).resolve().parents[1]
    models_dir = backend_dir / "models"
    img_dir = backend_dir.parent / "img"

    print("=" * 60)
    print("RUNNING REAL SAMPLE INFERENCE VERIFICATION")
    print("=" * 60)

    mgr = EngineManager(models_dir=models_dir, device="cpu")
    mgr.initialize()
    doc_service = DocumentService(mgr)

    sample_files = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.webp"))
    print(f"Found {len(sample_files)} sample file(s) in {img_dir}\n")

    for fpath in sample_files:
        print(f"--> Processing: {fpath.name}")
        with open(fpath, "rb") as f:
            content = f.read()

        resp = doc_service.extract_document(content, extract_tables=True)
        print(f"    Total pages : {resp.total_pages}")
        print(f"    Elapsed time: {resp.elapsed_ms:.2f} ms")
        print(f"    Lines found : {len(resp.pages[0].text_lines)}")
        print(f"    Layouts     : {[r.type for r in resp.pages[0].layout_regions]}")
        print(f"    Tables MD   : {len(resp.pages[0].tables_markdown)}")
        print(f"    Markdown Preview (first 200 chars):\n    {repr(resp.full_markdown[:200])}\n")

    print("=" * 60)
    print("ALL SAMPLE INFERENCES COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
