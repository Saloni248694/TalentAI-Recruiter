"""
Cross-encoder re-ranker for RAG.
Loads a small MS-MARCO cross-encoder that scores (query, passage) pairs directly,
giving far more accurate relevance than embedding cosine similarity alone.
Loads lazily and degrades gracefully if the model can't be loaded.
"""
import os

_cross_encoder = None
_reranker_available = False


def _load_reranker():
    """Lazy-load the cross-encoder model on first use."""
    global _cross_encoder, _reranker_available
    if _cross_encoder is not None:
        return
    try:
        from sentence_transformers import CrossEncoder
        # Small, fast, CPU-friendly re-ranking model (~80MB)
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        _reranker_available = True
        print("✅ Cross-encoder re-ranker loaded")
    except Exception as e:
        print(f"⚠️ Re-ranker unavailable ({e}) — using vector scores only")
        _reranker_available = False


def rerank(question: str, candidates: list, top_k: int = 5) -> list:
    """
    Re-score candidate chunks with the cross-encoder and return the top_k.
    `candidates` is a list of dicts each having a 'chunk' key.
    Falls back to the input order (already vector-sorted) if the model is unavailable.
    """
    if not candidates:
        return []

    _load_reranker()

    if not _reranker_available:
        # Graceful fallback: keep the existing vector-based order
        return candidates[:top_k]

    try:
        pairs = [(question, c["chunk"]) for c in candidates]
        scores = _cross_encoder.predict(pairs)
        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates[:top_k]
    except Exception as e:
        print(f"⚠️ Re-ranking failed ({e}) — using vector order")
        return candidates[:top_k]