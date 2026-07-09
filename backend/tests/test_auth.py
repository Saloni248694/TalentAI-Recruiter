"""Tests for authentication and security."""
from app.core.security import hash_password, verify_password


def test_password_hashing_roundtrip():
    pw = "MySecurePass123"
    hashed = hash_password(pw)
    assert hashed != pw                       # not stored as plaintext
    assert verify_password(pw, hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_different_hashes_for_same_password():
    # bcrypt salts each hash, so two hashes of same pw differ
    h1 = hash_password("samepass")
    h2 = hash_password("samepass")
    assert h1 != h2
    assert verify_password("samepass", h1)
    assert verify_password("samepass", h2)