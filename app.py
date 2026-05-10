import streamlit as st
import json
import re
import os
from google import genai
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bharat Samvidhan — Constitution AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent
PAGE_INDEX_PATH = BASE_DIR / "page_index.json"
MANIFEST_PATH = BASE_DIR / "page_manifest.json"
MODEL = "claude-sonnet-4-20250514"

# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_page_index():
    with open(PAGE_INDEX_PATH) as f:
        return json.load(f)

@st.cache_data
def load_manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)

page_index = load_page_index()
manifest = load_manifest()

# ── Anthropic client ─────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)

# ── RAG Pipeline ─────────────────────────────────────────────────────────────
def build_manifest_text(pages_subset=None):
    """Build a compact manifest string for the page selector LLM."""
    entries = pages_subset if pages_subset else manifest
    lines = []
    for p in entries:
        arts = "; ".join(p["article_titles"]) if p["article_titles"] else "—"
        lines.append(
            f"[Page {p['page']}] {p['part']} | Articles: {arts} | "
            f"Preview: {p['summary'][:120]}"
        )
    return "\n".join(lines)

def select_pages(query: str, top_k: int = 6) -> list[int]:
    """Stage 1: LLM reads the manifest and selects relevant page numbers."""
    client = get_client()
    manifest_text = build_manifest_text()

    prompt = f"""You are an expert on the Indian Constitution. Given a user query and 
a manifest of all 402 pages of the Constitution (each with a brief summary), 
select the {top_k} most relevant page numbers that would best answer the query.

Return ONLY a JSON array of page numbers, e.g.: [37, 42, 150, 201]
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
    # Parse page numbers robustly
    nums = re.findall(r'\d+', raw)
    page_nums = [int(n) for n in nums if 1 <= int(n) <= 402]
    return page_nums[:top_k]

def get_page_texts(page_nums: list[int]) -> list[dict]:
    """Retrieve full text for selected pages."""
    page_map = {p["page"]: p for p in page_index}
    result = []
    for num in page_nums:
        if num in page_map:
            result.append(page_map[num])
    return result

def synthesise_answer(query: str, pages: list[dict]) -> str:
    """Stage 2: LLM synthesises a cited answer from retrieved pages."""
    client = get_client()

    pages_text = ""
    for p in pages:
        pages_text += f"\n\n=== Page {p['page']} | {p['part']} ===\n{p['text']}"

    prompt = f"""You are a constitutional law expert specialising in the Indian Constitution.
Answer the user's question using ONLY the provided pages from the Constitution.

Rules:
1. Be precise and cite every claim as [Page N] inline.
2. Use plain English — explain legal language when needed.
3. If a question cannot be answered from the provided pages, say so clearly.
4. Structure the answer with a direct answer first, then elaboration.
5. Keep the response focused and authoritative.

User Question: {query}

Constitution Pages:
{pages_text}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/120px-Emblem_of_India.svg.png", width=80)
    st.title("Bharat Samvidhan")
    st.caption("Constitution of India — AI Assistant")
    st.divider()

    st.markdown("**Document loaded**")
    st.info(f"📄 Constitution of India\n\n402 pages · Updated to 106th Amendment (2023)")
    st.divider()

    st.markdown("**Settings**")
    top_k = st.slider("Pages to retrieve", min_value=3, max_value=10, value=6,
                      help="More pages = more thorough but slower answers")

    st.divider()
    st.markdown("**Browse by Part**")
    parts = sorted(set(p["part"] for p in manifest if "PART" in p["part"]))
    selected_part = st.selectbox("Jump to Part", ["All"] + parts, label_visibility="collapsed")

    st.divider()
    st.caption("Vectorless RAG · PageIndex method\nNo vector DB required")

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("⚖️ Indian Constitution — AI Legal Assistant")
st.caption("Ask any question about the Constitution of India. Every answer is grounded in the exact page of the document.")

# Sample queries
st.markdown("**Try a question:**")
sample_qs = [
    "What are the Fundamental Rights guaranteed to citizens?",
    "What is the procedure to amend the Constitution?",
    "What are the powers of the President of India?",
    "What does the Constitution say about freedom of speech?",
    "Explain the Directive Principles of State Policy",
    "What are the emergency provisions in the Constitution?",
    "What is the composition of the Supreme Court?",
    "What are the Fundamental Duties of citizens?",
]

cols = st.columns(4)
clicked_q = None
for i, q in enumerate(sample_qs):
    with cols[i % 4]:
        if st.button(q, key=f"sq_{i}", use_container_width=True):
            clicked_q = q

# Query input
query = st.text_input(
    "Your question",
    value=clicked_q or st.session_state.get("last_query", ""),
    placeholder="e.g. What is Article 21 about?",
    label_visibility="collapsed",
)

if clicked_q:
    st.session_state["last_query"] = clicked_q

ask_col, clear_col = st.columns([5, 1])
with ask_col:
    ask = st.button("Ask the Constitution ⚖️", type="primary", use_container_width=True)
with clear_col:
    if st.button("Clear", use_container_width=True):
        st.session_state["history"] = []
        st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state["history"] = []

if ask and query.strip():
    with st.spinner("🔍 Scanning PageIndex across 402 pages..."):
        try:
            selected_page_nums = select_pages(query, top_k=top_k)
        except Exception as e:
            st.error(f"Page selection failed: {e}")
            selected_page_nums = []

    if selected_page_nums:
        with st.spinner(f"📖 Retrieving {len(selected_page_nums)} pages & synthesising answer..."):
            try:
                retrieved_pages = get_page_texts(selected_page_nums)
                answer = synthesise_answer(query, retrieved_pages)
                st.session_state["history"].insert(0, {
                    "query": query,
                    "answer": answer,
                    "pages": retrieved_pages,
                    "page_nums": selected_page_nums,
                })
            except Exception as e:
                st.error(f"Answer generation failed: {e}")
    else:
        st.warning("Could not identify relevant pages. Try rephrasing your question.")

# ── Browse mode ───────────────────────────────────────────────────────────────
if selected_part != "All":
    st.divider()
    st.subheader(f"📑 {selected_part}")
    part_pages = [p for p in page_index if p["part"] == selected_part]
    st.caption(f"{len(part_pages)} pages in this part")
    for p in part_pages[:8]:
        with st.expander(f"Page {p['page']} — {', '.join(p['article_titles'][:2]) or 'Content'}"):
            st.text(p["text"][:800] + ("..." if len(p["text"]) > 800 else ""))

# ── Results ───────────────────────────────────────────────────────────────────
for i, item in enumerate(st.session_state["history"]):
    st.divider()
    st.markdown(f"### Q: {item['query']}")

    # Pipeline trace
    with st.expander("🔬 Pipeline trace", expanded=False):
        tr_cols = st.columns(3)
        with tr_cols[0]:
            st.metric("Stage 1 — PageIndex scan", "402 pages", "✓")
        with tr_cols[1]:
            st.metric("Stage 2 — Pages selected", len(item["page_nums"]), "✓")
        with tr_cols[2]:
            st.metric("Stage 3 — Answer generated", "1 response", "✓")
        st.caption(f"Pages retrieved: {item['page_nums']}")

    # Answer
    st.markdown(item["answer"])

    # Sources
    st.markdown("**📌 Sources**")
    src_cols = st.columns(min(len(item["pages"]), 3))
    for j, pg in enumerate(item["pages"]):
        with src_cols[j % 3]:
            arts = "\n".join(pg["article_titles"][:2]) if pg["article_titles"] else "Content"
            st.info(f"**Page {pg['page']}**\n\n{pg['part'][:50]}\n\n_{arts[:80]}_")

    # Show raw page text
    with st.expander("📄 View retrieved page texts"):
        for pg in item["pages"]:
            st.markdown(f"**Page {pg['page']}** — {pg['part']}")
            st.text(pg["text"][:600] + ("..." if len(pg["text"]) > 600 else ""))
            st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Constitution of India · As on 1st May 2024 · 106th Amendment Act 2023 · "
    "Built with Vectorless PageIndex RAG · Powered by Claude"
)
