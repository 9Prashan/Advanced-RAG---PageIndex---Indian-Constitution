# Bharat Samvidhan — Indian Constitution AI Assistant
### Vectorless RAG with PageIndex · No Vector DB Required

A complete end-to-end RAG project that lets you query all 402 pages of the
Indian Constitution (updated to the 106th Amendment, 2023) using natural language.
Every answer is grounded in exact page citations.

---

## Architecture — Vectorless PageIndex RAG

```
┌─────────────────────────────────────────────────────────┐
│  STAGE 1 — Ingestion (run once via build_index.py)      │
│  PDF → Page splitter → PageIndex JSON                   │
│  (402 pages · metadata · summaries · full text)         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 2 — Query Routing (per question)                 │
│  User query → LLM reads page_manifest.json              │
│  → Selects top 3–10 most relevant pages                 │
│  (No vector DB — pure LLM reasoning over the index)     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 3 — Answer Synthesis                             │
│  Full text of selected pages → LLM                      │
│  → Cited answer with [Page N] references                │
└─────────────────────────────────────────────────────────┘
```

**Why vectorless?** No embeddings, no FAISS, no Pinecone, no chunking heuristics.
The LLM reasons over a compact page manifest (summaries only) to decide which
pages to retrieve — then reads the full text of only those pages.

---

## Project Structure

```
constitution_rag/
├── app.py                    # Streamlit web app
├── query.py                  # CLI tool (no UI needed)
├── build_index.py            # Rebuild PageIndex from PDF
├── page_index.json           # Full PageIndex (402 pages + text)
├── page_manifest.json        # Compact manifest (for page selector LLM)
├── Consttution_of_india.pdf  # Source document
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# 1. Clone / download the project folder
cd constitution_rag

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 4a. Run the Streamlit web app
streamlit run app.py

# 4b. OR use the CLI
python query.py "What are the Fundamental Rights?"
python query.py "What is Article 21 about?" --top-k 4
python query.py --interactive
```

---

## Rebuilding the PageIndex

If you want to reprocess the PDF (e.g. different edition):

```bash
python build_index.py --pdf Consttution_of_india.pdf --out .
```

This regenerates `page_index.json` and `page_manifest.json`.

---

## Example Questions

| Question | What it demonstrates |
|---|---|
| What are the Fundamental Rights? | Multi-page synthesis (Part III) |
| What is Article 21? | Single article lookup |
| How can the Constitution be amended? | Procedural query (Part XX) |
| What are the powers of the President? | Cross-article aggregation |
| What does the Constitution say about untouchability? | Article 17 precision |
| Explain the Directive Principles | Part IV overview |
| What are emergency provisions? | Part XVIII |
| What are Fundamental Duties? | Part IVA |

---

## Key Design Decisions

**PageIndex structure per page:**
```json
{
  "page": 37,
  "part": "PART III — Fundamental Rights",
  "article_titles": ["Article 12: Definition", "Article 14: Equality before law"],
  "summary": "PART III FUNDAMENTAL RIGHTS General 12. Definition...",
  "char_count": 1946,
  "text": "...full page text..."
}
```

**Two-LLM pipeline:**
- LLM 1 (page selector): reads `page_manifest.json` — summaries only, ~60K tokens for all 402 pages
- LLM 2 (answer): reads full text of 3–10 selected pages — ~5–20K tokens per query

**Cost estimate:** ~$0.003–0.01 per query with Claude Sonnet 4.

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Claude Sonnet (`claude-sonnet-4-20250514`) |
| PDF parsing | pdfplumber |
| Vector DB | None ✓ |
| Embedding model | None ✓ |
| UI | Streamlit |
| Index storage | JSON files |

---

## Document Info

- **Source:** Constitution of India — Ministry of Law and Justice
- **Edition:** 6th pocket edition (diglot — Hindi + English)
- **Updated to:** 106th Amendment Act, 2023
- **Pages:** 402
- **Parts covered:** I through XXII + Schedules
