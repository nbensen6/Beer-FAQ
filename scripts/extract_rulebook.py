"""
One-time script to extract text from the Beer League Rulebook PDF.
The output (bot/rulebook.txt) is already committed to the repo,
so this script only needs to be re-run if the PDF is updated.

Usage:
    pip install pymupdf
    python scripts/extract_rulebook.py
"""

import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Install PyMuPDF first:  pip install pymupdf")
    sys.exit(1)

PDF_PATH = Path(__file__).parent.parent / "Assetts" / "Beer League Rulebook (v3.2).pdf"
OUTPUT_PATH = Path(__file__).parent.parent / "bot" / "rulebook.txt"


def extract() -> str:
    doc = fitz.open(str(PDF_PATH))
    pages: list[str] = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        # Clean up common PDF artifacts
        text = text.replace("\u200b", "")  # zero-width spaces
        text = re.sub(r"\n{3,}", "\n\n", text)  # collapse excessive newlines
        text = text.strip()
        pages.append(f"[Page {i}]\n\n{text}")

    doc.close()
    return "\n\n---\n\n".join(pages)


def main() -> None:
    if not PDF_PATH.exists():
        print(f"PDF not found at {PDF_PATH}")
        sys.exit(1)

    text = extract()
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(f"Extracted {len(text)} characters to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
