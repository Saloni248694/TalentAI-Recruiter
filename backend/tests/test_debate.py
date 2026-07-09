"""Tests for the debate pipeline (mock mode, no API needed)."""
from app.agents.debate import mock_debate, run_debate


def test_mock_debate_structure():
    result = mock_debate("Test Candidate")
    assert "advocate_case" in result
    assert "skeptic_case" in result
    assert "rebuttal" in result
    assert "verdict" in result
    assert result["verdict"]["recommendation"] in ("shortlist", "reject", "borderline")


def test_run_debate_force_mock():
    result = run_debate(
        resume_text="Python developer",
        job_description="Looking for Python engineer",
        candidate_name="Test",
        force_mock=True
    )
    assert result["is_mock"] is True
    assert result["pipeline"] == ["advocate", "skeptic", "rebuttal", "judge"]


def test_run_debate_falls_back_without_llm():
    """Without credits, run_debate returns a mock transcript instead of crashing."""
    result = run_debate(
        resume_text="Some resume",
        job_description="Some job",
        candidate_name="Candidate",
        force_mock=False   # llm unavailable -> auto mock
    )
    assert "verdict" in result
    assert result["verdict"]["recommendation"] in ("shortlist", "reject", "borderline")