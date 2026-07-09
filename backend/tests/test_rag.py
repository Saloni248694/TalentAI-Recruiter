"""Test hybrid RAG retrieval (no API needed)."""
from app.services.rag import chunk_text, retrieve_chunks


def test_chunk_text_overlaps():
    chunks = chunk_text("a" * 1200, chunk_size=500, overlap=100)
    assert len(chunks) >= 2


def test_retrieve_returns_relevant_candidate():
    resumes = [
        {"id": 1, "candidate_name": "Alice", "parsed_text": "Expert in Python and Docker and Kubernetes.", "skills_text": "Python, Docker"},
        {"id": 2, "candidate_name": "Bob", "parsed_text": "Professional chef, Italian cuisine.", "skills_text": "Cooking"},
    ]
    results = retrieve_chunks("Who knows Kubernetes?", resumes, vector_k=5, final_k=3)
    assert len(results) > 0
    # Alice should surface for a Kubernetes query
    assert any(r["candidate_name"] == "Alice" for r in results)