"""
RAG over the talent pool — chunk resumes, retrieve relevant pieces via FAISS,
synthesize an answer with Claude that cites specific candidates.
Retrieval works without API; synthesis auto-activates when credits available.
"""
import numpy as np
from app.services.llm import ask_claude, llm_available
from app.services.matcher import get_embedding


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


def retrieve_chunks(question: str, resumes: list, top_k: int = 8) -> list:
    """Embed question, score every resume chunk, return top_k with candidate refs."""
    q_vec = get_embedding(question[:1000])

    scored = []
    for r in resumes:
        full = (r["parsed_text"] or "") + " Skills: " + (r["skills_text"] or "")
        for chunk in chunk_text(full):
            if not chunk.strip():
                continue
            c_vec = get_embedding(chunk[:1000])
            score = _cosine(q_vec, c_vec)
            scored.append({
                "resume_id": r["id"],
                "candidate_name": r["candidate_name"],
                "chunk": chunk,
                "score": score
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def answer_question(question: str, resumes: list, history: list = None) -> dict:
    """Full RAG: retrieve relevant chunks + synthesize a cited answer."""
    chunks = retrieve_chunks(question, resumes)

    if not chunks or chunks[0]["score"] < 0.15:
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
        # Retrieval-only fallback: list the matched candidates
        names = ", ".join(seen.values())
        return {
            "answer": f"Based on your talent pool, these candidates appear most relevant "
                      f"to your question: {names}. (Connect the Claude API for full "
                      f"natural-language answers.)",
            "citations": citations,
            "llm_used": False
        }

    # Build context block for Claude
    context = "\n\n".join(
        f"[Candidate: {c['candidate_name']} (id:{c['resume_id']})]\n{c['chunk']}"
        for c in chunks
    )

    history_block = ""
    if history:
        recent = history[-4:]  # last 2 Q&A pairs
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