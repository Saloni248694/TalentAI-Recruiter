"""
Resume Consistency Auditor — fraud/inflation detection.
Rule-based timeline + claim analysis (works without API).
Optional Claude audit pass adds LLM reasoning when credits available.
"""
import re
from datetime import datetime
from dateutil import parser as dateparser
from app.services.llm import ask_claude_json, llm_available


# ── Date extraction helpers ──────────────────────

MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"

# Matches: "Jan 2020 - Mar 2022", "2019-2021", "June 2021 to Present"
DATE_RANGE_PATTERN = re.compile(
    rf"({MONTHS}\.?\s+\d{{4}}|\d{{4}})\s*(?:-|–|—|to)\s*"
    rf"({MONTHS}\.?\s+\d{{4}}|\d{{4}}|present|current|now)",
    re.IGNORECASE
)


def _parse_date(s: str, default_end: bool = False):
    """Parse a date string; 'present' becomes today."""
    s = s.strip().lower()
    if s in ("present", "current", "now"):
        return datetime.now()
    try:
        # Year-only like "2019" -> Jan 1 (or Dec 31 if end of a range)
        if re.fullmatch(r"\d{4}", s):
            year = int(s)
            return datetime(year, 12, 31) if default_end else datetime(year, 1, 1)
        return dateparser.parse(s, fuzzy=True)
    except Exception:
        return None


def extract_date_ranges(text: str) -> list:
    """Find all date ranges in resume text -> [(start, end, context_line)]"""
    ranges = []
    for line in text.split("\n"):
        for m in DATE_RANGE_PATTERN.finditer(line):
            start = _parse_date(m.group(1))
            end = _parse_date(m.group(3), default_end=True)
            if start and end and start <= end:
                ranges.append({
                    "start": start,
                    "end": end,
                    "context": line.strip()[:90]
                })
    return ranges


# ── Rule-based checks ────────────────────────────

def check_overlaps(ranges: list) -> list:
    """Flag overlapping employment periods (>60 days overlap)."""
    flags = []
    sorted_r = sorted(ranges, key=lambda r: r["start"])
    for i in range(len(sorted_r)):
        for j in range(i + 1, len(sorted_r)):
            a, b = sorted_r[i], sorted_r[j]
            overlap_days = (min(a["end"], b["end"]) - max(a["start"], b["start"])).days
            if overlap_days > 60:
                flags.append({
                    "type": "timeline_overlap",
                    "severity": "warning",
                    "detail": f"Overlapping periods ({overlap_days} days): "
                              f"'{a['context'][:45]}' and '{b['context'][:45]}'"
                })
    return flags


def check_gaps(ranges: list) -> list:
    """Flag unexplained gaps > 6 months between consecutive periods."""
    flags = []
    sorted_r = sorted(ranges, key=lambda r: r["start"])
    for i in range(len(sorted_r) - 1):
        gap_days = (sorted_r[i + 1]["start"] - sorted_r[i]["end"]).days
        if gap_days > 183:
            flags.append({
                "type": "employment_gap",
                "severity": "info",
                "detail": f"Gap of ~{gap_days // 30} months between "
                          f"'{sorted_r[i]['context'][:40]}' and '{sorted_r[i+1]['context'][:40]}'"
            })
    return flags


def check_experience_math(text: str, ranges: list) -> list:
    """Compare claimed 'X years of experience' vs. earliest date found."""
    flags = []
    claim = re.search(r"(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", text, re.IGNORECASE)
    if claim and ranges:
        claimed_years = int(claim.group(1))
        earliest = min(r["start"] for r in ranges)
        actual_years = (datetime.now() - earliest).days / 365.25
        if claimed_years > actual_years + 1.5:  # tolerance
            flags.append({
                "type": "experience_inflation",
                "severity": "red-flag",
                "detail": f"Claims {claimed_years} years experience, but earliest "
                          f"date found is {earliest.year} (~{actual_years:.1f} years)"
            })
    return flags


def check_title_velocity(text: str) -> list:
    """Flag suspiciously fast seniority progression keywords."""
    flags = []
    tl = text.lower()
    junior_hit = re.search(r"\b(junior|intern|trainee|fresher)\b", tl)
    senior_hit = re.search(r"\b(director|vp|vice president|head of|chief|cto|ceo)\b", tl)
    if junior_hit and senior_hit:
        # Only meaningful with dates, so keep as info-level nudge
        flags.append({
            "type": "title_velocity",
            "severity": "info",
            "detail": "Resume contains both junior-level and executive-level titles — "
                      "verify progression timeline in interview"
        })
    return flags


def check_skill_support(text: str, skills: list) -> list:
    """Flag skills claimed but never mentioned outside the skills section."""
    flags = []
    if not skills:
        return flags
    # Crude: count occurrences of each skill in full text
    unsupported = [s for s in skills if text.lower().count(s.lower()) <= 1]
    if len(unsupported) >= max(3, len(skills) // 2):
        flags.append({
            "type": "unsupported_skills",
            "severity": "warning",
            "detail": f"{len(unsupported)} claimed skills appear only in the skills list "
                      f"with no supporting project/role context: {', '.join(unsupported[:6])}"
        })
    return flags


# ── LLM audit pass (auto-enables when credits available) ──

def llm_audit(text: str) -> list:
    """Ask Claude to flag implausible claims. Returns [] gracefully on failure."""
    if not llm_available:
        return []
    try:
        system = ("You are a resume fraud auditor. Respond with ONLY valid JSON, "
                  "no markdown fences.")
        prompt = f"""Audit this resume for implausible or inflated claims.
Return ONLY JSON: {{"flags": [{{"type": "llm_audit", "severity": "info|warning|red-flag", "detail": "specific claim + why it's suspicious"}}]}}
Maximum 4 flags. If nothing suspicious, return {{"flags": []}}.

RESUME:
{text[:5000]}"""
        result = ask_claude_json(prompt, system=system, max_tokens=800)
        return result.get("flags", [])[:4]
    except Exception as e:
        print(f"⚠️ LLM audit skipped ({e})")
        return []


# ── Main entry point ─────────────────────────────

def audit_resume(text: str, skills: list = None) -> dict:
    """Run full consistency audit. Returns score + flagged items."""
    ranges = extract_date_ranges(text)

    flags = []
    flags += check_overlaps(ranges)
    flags += check_gaps(ranges)
    flags += check_experience_math(text, ranges)
    flags += check_title_velocity(text)
    flags += check_skill_support(text, skills or [])
    flags += llm_audit(text)          # no-op until credits available

    # Score: start 100, deduct by severity
    deductions = {"info": 3, "warning": 10, "red-flag": 25}
    score = 100 - sum(deductions.get(f["severity"], 5) for f in flags)
    score = max(0, min(100, score))

    return {
        "consistency_score": score,
        "date_ranges_found": len(ranges),
        "total_flags": len(flags),
        "flags": flags,
        "llm_audit_included": llm_available
    }