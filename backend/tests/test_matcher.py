"""Tests for embeddings and similarity math."""
from app.services.matcher import get_embedding


def test_embedding_has_correct_dimensions():
    vec = get_embedding("Python developer")
    assert len(vec) == 384  # all-MiniLM-L6-v2 dimension


def test_embedding_is_deterministic():
    v1 = get_embedding("machine learning engineer")
    v2 = get_embedding("machine learning engineer")
    # Same text -> same vector
    assert list(v1) == list(v2)


def test_identical_text_more_similar_than_different():
    import numpy as np

    def cosine(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    base = get_embedding("Python backend developer with FastAPI")
    same = get_embedding("Python backend developer with FastAPI")
    diff = get_embedding("Professional chef specializing in Italian cuisine")

    assert cosine(base, same) > cosine(base, diff)