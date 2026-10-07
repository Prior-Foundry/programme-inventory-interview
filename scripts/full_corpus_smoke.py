#!/usr/bin/env python3
"""Offline preflight for a downloaded corpus; does not modify inventory JSON."""
from __future__ import annotations

import sys
from pathlib import Path


root = Path(__file__).resolve().parents[1]
corpus = root / "corpus"
pdfs = sorted(corpus.glob("*.pdf"))
if not pdfs:
    raise SystemExit("No PDFs found. Run scripts/fetch-corpus first.")
def has_pdf_header(pdf: Path) -> bool:
    with pdf.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


invalid = [pdf for pdf in pdfs if pdf.stat().st_size == 0 or not has_pdf_header(pdf)]
print(f"Found {len(pdfs)} PDFs ({sum(pdf.stat().st_size for pdf in pdfs) / 1024 / 1024:.1f} MB).")
if invalid:
    print("Invalid PDF headers:", *[pdf.name for pdf in invalid], sep="\n", file=sys.stderr)
    raise SystemExit(1)
