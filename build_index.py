"""
build_index.py — PageIndex builder for the Indian Constitution RAG pipeline.

Run this once to generate page_index.json and page_manifest.json from the PDF.
Usage:
    python build_index.py --pdf Consttution_of_india.pdf
"""

import argparse
import json
import re
from pathlib import Path
import pdfplumber

PARTS = {
    "PART I": "The Union and its Territory",
    "PART II": "Citizenship",
    "PART III": "Fundamental Rights",
    "PART IV": "Directive Principles of State Policy",
    "PART IVA": "Fundamental Duties",
    "PART V": "The Union",
    "PART VI": "The States",
    "PART VIII": "The Union Territories",
    "PART IX": "The Panchayats",
    "PART IXA": "The Municipalities",
    "PART X": "The Scheduled and Tribal Areas",
    "PART XI": "Relations between the Union and the States",
    "PART XII": "Finance, Property, Contracts and Suits",
    "PART XIII": "Trade, Commerce and Intercourse",
    "PART XIV": "Services under the Union and the States",
    "PART XV": "Elections",
    "PART XVI": "Special Provisions — Certain Classes",
    "PART XVII": "Official Language",
    "PART XVIII": "Emergency Provisions",
    "PART XIX": "Miscellaneous",
    "PART XX": "Amendment of the Constitution",
    "PART XXI": "Temporary Provisions",
    "PART XXII": "Short Title, Commencement",
}


def extract_english_text(raw: str) -> str:
    lines = raw.split("\n")
    english = [
        l for l in lines
        if l.strip() and sum(1 for c in l if ord(c) < 128) / max(len(l), 1) > 0.6
    ]
    return "\n".join(english).strip()


def build_index(pdf_path: str, out_dir: str = "."):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    page_index = []
    current_part = "Preamble / Preliminary"

    print(f"Opening {pdf_path}...")
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Total pages: {total}")

        for i, page in enumerate(pdf.pages):
            raw = page.extract_text() or ""
            text = extract_english_text(raw)

            # Track current Part
            for part_key in sorted(PARTS.keys(), key=len, reverse=True):
                if part_key in text:
                    current_part = f"{part_key} — {PARTS[part_key]}"
                    break

            # Extract article headings
            art_matches = re.findall(
                r'\b(\d{1,3}[A-Z]?)\.\s+([A-Z][A-Za-z ,\-]{5,60}?)[\.\—]', text
            )
            article_titles = [f"Article {a[0]}: {a[1].strip()}" for a in art_matches[:4]]

            # Summary = first 400 chars cleaned
            summary = re.sub(r'^\d+\s+THE CONSTITUTION OF INDIA\s*', '', text)
            summary = re.sub(r'\([ivx]+\)\s*Contents', '', summary)
            summary = summary[:400].replace("\n", " ").strip()

            entry = {
                "page": i + 1,
                "part": current_part,
                "article_titles": article_titles,
                "summary": summary,
                "char_count": len(text),
                "text": text,
            }
            page_index.append(entry)

            if (i + 1) % 50 == 0:
                print(f"  Processed {i+1}/{total} pages...")

    # Full index (with text)
    idx_path = out / "page_index.json"
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(page_index, f, ensure_ascii=False, indent=2)
    print(f"Saved: {idx_path}")

    # Manifest (without text — for page selector LLM)
    manifest = [
        {k: v for k, v in p.items() if k != "text"}
        for p in page_index
    ]
    man_path = out / "page_manifest.json"
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Saved: {man_path}")

    print(f"\nDone. PageIndex built: {len(page_index)} pages.")
    return page_index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build PageIndex from Constitution PDF")
    parser.add_argument("--pdf", default="Consttution_of_india.pdf", help="Path to PDF")
    parser.add_argument("--out", default=".", help="Output directory")
    args = parser.parse_args()
    build_index(args.pdf, args.out)
