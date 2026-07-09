"""Tests for the resume parser and its heuristic fallback."""
from unittest.mock import patch
from app.services.parser import is_likely_name, parse_resume_with_regex


def test_is_likely_name_accepts_real_name():
    assert is_likely_name("Rahul Sharma") is True


def test_is_likely_name_rejects_section_header():
    assert is_likely_name("WORK EXPERIENCE AND PROJECTS DONE") is False


def test_is_likely_name_rejects_fragment_with_period():
    assert is_likely_name("recommendation relevance.") is False


def test_is_likely_name_rejects_email():
    assert is_likely_name("john@example.com") is False


def test_regex_parser_extracts_email():
    text = "Rahul Sharma\nrahul@example.com\n+91-9876543210\nPython developer"
    result = parse_resume_with_regex(text)
    assert result["email"] == "rahul@example.com"


def test_regex_parser_extracts_skills():
    text = "Experienced in Python, Docker, and AWS."
    result = parse_resume_with_regex(text)
    assert "Python" in result["skills"]
    assert "Docker" in result["skills"]


def test_regex_parser_filename_fallback():
    # No detectable name in text -> use filename
    text = "email@test.com\nsome random content here"
    result = parse_resume_with_regex(text, filename="John_Doe_Resume.pdf")
    assert result["candidate_name"] == "John Doe"


def test_parser_falls_back_when_llm_unavailable():
    """If Claude is unavailable, parse_resume_with_claude uses regex fallback."""
    with patch("app.services.parser.llm_available", False):
        from app.services.parser import parse_resume_with_claude
        result = parse_resume_with_claude("Rahul\nrahul@test.com\nPython", filename="test.pdf")
        assert result["candidate_name"]  # got a name
        assert result["email"] == "rahul@test.com"