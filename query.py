"""
query.py — CLI interface for the Indian Constitution RAG pipeline.

Usage:
    python query.py "What are the Fundamental Rights?"
    python query.py "What is Article 21?" --top-k 4
    python query.py --interactive
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
import anthropic

BASE_DIR = Path(__file__).parent
MODEL = "claude-sonnet-4-20250514"


def load_data():
    with open(BASE_DIR / "page_index.json") as f:
        page_index = json.load(f)
    with open(BASE_DIR / "page_manifest.json") as f:
        manifest = json.load(f)
    return page_index, manifest


def build_manifest_text(manifest):
    lines = []
    for p in manifest:
        arts = "; ".join(p["article_titles"]) if p["article_titles"] else "—"
        lines.append(
            f"[Page {p['page']}] {p['part']} | {arts} | {p['summary'][:120]}"
        )
    return "\n".join(lines)


def select_pages(client, query, manifest, top_k=6):
    manifest_text = build_manifest_text(manifest)
    prompt = f"""You are an expert on the Indian Constitution. Select the {top_k} most 
relevant page numbers from the manifest that would best answer the user's query.

Return ONLY a JSON array of page numbers, e.g.: [37, 42, 150]
No explanation. No markdown. Just the JSON array.

User Query: {query}

Page Manifest:
{manifest_text}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    nums = re.findall(r'\d+', raw)
    return [int(n) for n in nums if 1 <= int(n) <= 402][:top_k]


def get_page_texts(page_index, page_nums):
    page_map = {p["page"]: p for p in page_index}
    return [page_map[n] for n in page_nums if n in page_map]


def synthesise_answer(client, query, pages):
    pages_text = ""
    for p in pages:
        pages_text += f"\n\n=== Page {p['page']} | {p['part']} ===\n{p['text']}"

    prompt = f"""You are a constitutional law expert specialising in the Indian Constitution.
Answer the user's question using ONLY the provided pages from the Constitution.

Rules:
1. Be precise and cite every claim as [Page N] inline.
2. Explain legal language in plain English when needed.
3. If the answer is not in the provided pages, say so clearly.
4. Structure: direct answer first, then elaboration.

User Question: {query}

Constitution Pages:
{pages_text}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def ask(client, page_index, manifest, query, top_k=6):
    print(f"\n{'='*60}")
    print(f"Q: {query}")
    print(f"{'='*60}")

    print("⏳ Stage 1: Scanning PageIndex (402 pages)...")
    page_nums = select_pages(client, query, manifest, top_k)
    print(f"✓  Selected pages: {page_nums}")

    print("⏳ Stage 2: Retrieving full text & synthesising answer...")
    pages = get_page_texts(page_index, page_nums)
    answer = synthesise_answer(client, query, pages)

    print(f"\n📜 Answer:\n{answer}")
    print(f"\n📌 Sources: Pages {page_nums}")
    for p in pages:
        arts = ", ".join(p["article_titles"][:2]) or "—"
        print(f"   • Page {p['page']}: {p['part']} | {arts}")


def main():
    parser = argparse.ArgumentParser(description="Query the Indian Constitution with RAG")
    parser.add_argument("query", nargs="?", help="Question to ask")
    parser.add_argument("--top-k", type=int, default=6, help="Pages to retrieve (default 6)")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    page_index, manifest = load_data()
    print(f"Loaded PageIndex: {len(page_index)} pages")

    if args.interactive:
        print("\nIndian Constitution RAG — Interactive Mode")
        print("Type 'quit' to exit\n")
        while True:
            try:
                q = input("Your question: ").strip()
                if q.lower() in ("quit", "exit", "q"):
                    break
                if q:
                    ask(client, page_index, manifest, q, args.top_k)
            except KeyboardInterrupt:
                break
    elif args.query:
        ask(client, page_index, manifest, args.query, args.top_k)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
