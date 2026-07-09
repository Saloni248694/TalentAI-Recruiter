"""Tests for the ATS scoring engine."""
from app.services.ats import analyze_ats


def test_ats_returns_score():
    result = analyze_ats("Experienced Python developer with 5 years in FastAPI and SQL.")
    assert "ats_score" in result
    assert 0 <= result["ats_score"] <= 100


def test_ats_empty_text():
    result = analyze_ats("")
    assert "ats_score" in result
    assert result["ats_score"] >= 0


def test_ats_rich_resume_scores_higher_than_sparse():
    sparse = analyze_ats("John. Email. Phone.")
    rich = analyze_ats(
        "Senior Software Engineer. Led a team of 8. Developed scalable APIs "
        "in Python and FastAPI. Improved performance by 40%. Managed PostgreSQL "
        "databases. Experience: 2018-2023. Education: B.Tech Computer Science. "
        "Skills: Python, Docker, AWS, React, SQL. Built microservices architecture."
    )
    assert rich["ats_score"] >= sparse["ats_score"]


def test_ats_score_is_deterministic():
    text = "Python developer with Docker and AWS experience. Built REST APIs."
    r1 = analyze_ats(text)
    r2 = analyze_ats(text)
    assert r1["ats_score"] == r2["ats_score"]


def test_ats_huge_text_does_not_crash():
    huge = "Python developer. " * 5000
    result = analyze_ats(huge)
    assert 0 <= result["ats_score"] <= 100