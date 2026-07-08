"""
JD What-If Simulator — requirement elasticity analysis.
Extracts toggleable requirement chips from a JD, then re-runs FAISS matching
with modified requirements to show how the candidate pool changes.
Chip extraction uses Claude when available, keyword heuristics otherwise.
"""
import re
import numpy as np
from app.services.llm import ask_claude_json, llm_available
from app.services.matcher import get_embedding


# ── Requirement chip extraction ──────────────────

COMMON_REQUIREMENTS = [
    "Python", "JavaScript", "React", "Node", "FastAPI", "Django", "SQL",
    "PostgreSQL", "MySQL", "MongoDB", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "Machine Learning", "Deep Learning", "Java", "C++", "TypeScript", "REST", "API",
    "Bachelor", "Master", "PhD", "degree", "certification",
    "Git", "CI/CD", "Agile", "microservices", "TensorFlow", "PyTorch",
    "NLP", "Computer Vision", "Data Science", "Spark", "Kafka", "GraphQL"
]


def extract_requirements(jd_text: str) -> list:
    """Extract discrete requirement chips from a job description."""
    if llm_available:
        try:
            system = "You extract job requirements. Respond ONLY with valid JSON, no fences."
            prompt = f"""Extract discrete, toggleable requirements from this job description.
Return ONLY JSON: {{"requirements": ["req1", "req2", ...]}}
Each requirement should be a short phrase (skill, qualification, or experience).
Maximum 12 requirements.

JOB DESCRIPTION:
{jd_text[:3000]}"""
            result = ask_claude_json(prompt, system=system, max_tokens=600)
            reqs = result.get("requirements", [])
            if reqs:
                return reqs[:12]
        except Exception as e:
            print(f"⚠️ LLM requirement extraction skipped ({e}) — using keyword fallback")

    # Keyword fallback
    found = []
    jd_lower = jd_text.lower()
    for kw in COMMON_REQUIREMENTS:
        if kw.lower() in jd_lower and kw not in found:
            found.append(kw)
    return found[:12]


# ── Matching helpers ─────────────────────────────

def _cosine(a, b):
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def match_pool(effective_jd: str, resumes: list) -> list:
    """Score every resume against the effective JD text. Returns sorted list."""
    jd_vec = get_embedding(effective_jd[:2000])
    scored = []
    for r in resumes:
        text = (r["parsed_text"] or "") + " " + (r["skills_text"] or "")
        r_vec = get_embedding(text[:2000])
        score = round(max(0.0, _cosine(jd_vec, r_vec)) * 100, 2)
        scored.append({
            "resume_id": r["id"],
            "candidate_name": r["candidate_name"],
            "match_score": score
        })
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored


def simulate(original_jd: str, resumes: list, removed: list, added: list,
             threshold: float = 40.0) -> dict:
    """Compare original vs. modified JD candidate pools."""

    # Build effective JD text
    effective = original_jd
    for req in (removed or []):
        effective = re.sub(re.escape(req), "", effective, flags=re.IGNORECASE)
    if added:
        effective += " " + " ".join(added)

    original_ranked = match_pool(original_jd, resumes)
    modified_ranked = match_pool(effective, resumes)

    def above(ranked):
        return [c for c in ranked if c["match_score"] >= threshold]

    orig_pool = above(original_ranked)
    mod_pool = above(modified_ranked)

    orig_avg = round(sum(c["match_score"] for c in original_ranked) / len(original_ranked), 1) if original_ranked else 0
    mod_avg = round(sum(c["match_score"] for c in modified_ranked) / len(modified_ranked), 1) if modified_ranked else 0

    # Rank movers
    orig_rank = {c["resume_id"]: i for i, c in enumerate(original_ranked)}
    movers = []
    for i, c in enumerate(modified_ranked):
        old = orig_rank.get(c["resume_id"], i)
        delta = old - i
        if delta != 0:
            movers.append({
                "candidate_name": c["candidate_name"],
                "movement": delta,          # positive = moved up
                "new_score": c["match_score"]
            })
    movers.sort(key=lambda m: abs(m["movement"]), reverse=True)

    pool_delta = len(mod_pool) - len(orig_pool)
    pool_pct = round((pool_delta / len(orig_pool)) * 100, 1) if orig_pool else 0

    return {
        "original": {"pool_size": len(orig_pool), "avg_score": orig_avg,
                     "ranked": original_ranked[:10]},
        "simulated": {"pool_size": len(mod_pool), "avg_score": mod_avg,
                      "ranked": modified_ranked[:10]},
        "deltas": {
            "pool_size_change": pool_delta,
            "pool_size_pct": pool_pct,
            "avg_score_change": round(mod_avg - orig_avg, 1)
        },
        "top_movers": movers[:5],
        "removed": removed or [],
        "added": added or []
    }