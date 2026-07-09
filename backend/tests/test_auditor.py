"""Tests for the Consistency Auditor (timeline analysis)."""
from app.services.auditor import (
    extract_date_ranges, check_overlaps, check_experience_math, audit_resume
)


def test_extract_date_ranges_finds_ranges():
    text = "Software Engineer Jan 2020 - Mar 2022 at TechCorp"
    ranges = extract_date_ranges(text)
    assert len(ranges) >= 1


def test_clean_timeline_has_no_overlap():
    text = "Role A Jan 2018 - Dec 2019\nRole B Jan 2020 - Dec 2021"
    ranges = extract_date_ranges(text)
    flags = check_overlaps(ranges)
    assert len(flags) == 0


def test_overlapping_timeline_is_flagged():
    text = "Role A Jan 2019 - Dec 2021\nRole B Jan 2020 - Dec 2022"
    ranges = extract_date_ranges(text)
    flags = check_overlaps(ranges)
    assert len(flags) >= 1
    assert flags[0]["type"] == "timeline_overlap"


def test_experience_inflation_flagged():
    # Claims 15 years but earliest date is recent
    text = "15 years of experience. Worked 2022 - 2023 at StartupX."
    ranges = extract_date_ranges(text)
    flags = check_experience_math(text, ranges)
    assert any(f["type"] == "experience_inflation" for f in flags)


def test_audit_returns_score_and_structure():
    text = "Python developer. Role Jan 2020 - Dec 2022 at Acme."
    result = audit_resume(text, skills=["Python"])
    assert "consistency_score" in result
    assert 0 <= result["consistency_score"] <= 100
    assert "flags" in result
    assert isinstance(result["flags"], list)


def test_audit_no_llm_when_unavailable():
    # llm_audit_included reflects client state; audit still works either way
    result = audit_resume("Some resume text with dates 2020 - 2022.", skills=[])
    assert "llm_audit_included" in result