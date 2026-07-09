"""
RAG over the talent pool — HYBRID retrieval (BM25 keyword + vector) followed by
a cross-encoder re-ranking pass, then Claude synthesis with candidate citations.
Every stage degrades gracefully if a dependency or the API is unavailable.
"""
import re
import numpy as np
from rank_bm25 import BM25Okapi

from app.services.llm import ask_claude, llm_available
from app.services.matcher import get_embedding
from app.services.reranker import rerank


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """Split text into overlapping character chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _cosine(a, b):
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def _tokenize(text: str) -> list:
    """Simple lowercase word tokenizer for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


def _build_chunk_pool(resumes: list) -> list:
    """Flatten all resumes into a list of chunk records."""
    pool = []
    for r in resumes:
        full = (r["parsed_text"] or "") + " Skills: " + (r["skills_text"] or "")
        for chunk in chunk_text(full):
            if chunk.strip():
                pool.append({
                    "resume_id": r["id"],
                    "candidate_name": r["candidate_name"],
                    "chunk": chunk
                })
    return pool


def retrieve_chunks(question: str, resumes: list,
                    vector_k: int = 20, final_k: int = 8) -> list:
    """
    HYBRID retrieval + re-ranking:
      1. Vector search (semantic)  -> catches meaning / synonyms
      2. BM25 keyword search       -> catches exact terms
      3. Merge the two candidate sets (union, deduplicated)
      4. Cross-encoder re-rank     -> precise final ordering
    Returns the top `final_k` chunks with candidate references.
    """
    pool = _build_chunk_pool(resumes)
    if not pool:
        return []

    # ── Stage 1: Vector search ──
    q_vec = get_embedding(question[:1000])
    for c in pool:
        c["vector_score"] = _cosine(q_vec, get_embedding(c["chunk"][:1000]))
    vector_top = sorted(pool, key=lambda x: x["vector_score"], reverse=True)[:vector_k]

    # ── Stage 2: BM25 keyword search ──
    tokenized_corpus = [_tokenize(c["chunk"]) for c in pool]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(_tokenize(question))
    for c, s in zip(pool, bm25_scores):
        c["bm25_score"] = float(s)
    bm25_top = sorted(pool, key=lambda x: x["bm25_score"], reverse=True)[:vector_k]

    # ── Stage 3: Merge (union, dedup by chunk identity) ──
    merged = {}
    for c in vector_top + bm25_top:
        key = (c["resume_id"], c["chunk"][:50])
        merged[key] = c
    candidates = list(merged.values())

    # ── Stage 4: Cross-encoder re-rank ──
    reranked = rerank(question, candidates, top_k=final_k)
    return reranked


def answer_question(question: str, resumes: list, history: list = None) -> dict:
    """Full RAG: hybrid retrieve + re-rank + synthesize a cited answer."""
    chunks = retrieve_chunks(question, resumes)

    # Relevance guardrail — use whichever score is present
    def _best_score(c):
        return c.get("rerank_score", c.get("vector_score", 0))

    if not chunks or _best_score(chunks[0]) < -5:  # cross-encoder scores can be negative
        # only bail if truly nothing retrieved
        if not chunks:
            return {
                "answer": "I couldn't find any candidates in your talent pool relevant to that question.",
                "citations": [],
                "llm_used": False
            }

    # Build unique citation list
    seen = {}
    for c in chunks:
        if c["resume_id"] not in seen:
            seen[c["resume_id"]] = c["candidate_name"]
    citations = [{"resume_id": rid, "candidate_name": name} for rid, name in seen.items()]

    if not llm_available:
        names = ", ".join(seen.values())
        return {
            "answer": f"Based on your talent pool (hybrid search + re-ranking), these candidates "
                      f"appear most relevant: {names}. (Connect the Claude API for full "
                      f"natural-language answers.)",
            "citations": citations,
            "llm_used": False
        }

    # Build context for Claude
    context = "\n\n".join(
        f"[Candidate: {c['candidate_name']} (id:{c['resume_id']})]\n{c['chunk']}"
        for c in chunks
    )

    history_block = ""
    if history:
        recent = history[-4:]
        history_block = "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    system = ("You are a recruitment assistant answering questions about a talent pool. "
              "Answer ONLY using the provided candidate context. Cite candidates by name. "
              "If the context doesn't contain the answer, say so honestly.")

    prompt = f"""{f'Recent conversation:{chr(10)}{history_block}{chr(10)}{chr(10)}' if history_block else ''}Candidate context from the talent pool:
{context}

Question: {question}

Answer concisely, citing specific candidate names as evidence."""

    try:
        answer = ask_claude(prompt, system=system, max_tokens=700)
        return {"answer": answer, "citations": citations, "llm_used": True}
    except Exception as e:
        names = ", ".join(seen.values())
        return {
            "answer": f"Relevant candidates: {names}. (AI synthesis unavailable: {e})",
            "citations": citations,
            "llm_used": False
        }