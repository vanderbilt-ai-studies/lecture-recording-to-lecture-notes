#!/usr/bin/env python3
"""Convert a PDF file to individual PNG slide images using pymupdf."""

import argparse
import os
import sys

try:
    import fitz  # pymupdf
except ImportError:
    print("pymupdf not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf", "-q"])
    import fitz


def convert(pdf_path: str, output_dir: str, dpi: int = 200):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        pix.save(os.path.join(output_dir, f"slide-{i+1:03d}.png"))
    doc.close()
    print(f"Converted {len(doc)} slides to {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to slide PNGs")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("output_dir", help="Directory to save PNGs (e.g., slides/)")
    parser.add_argument("--dpi", type=int, default=200, help="Resolution (default: 200)")
    args = parser.parse_args()
    convert(args.pdf_path, args.output_dir, args.dpi)
