"""
Multi-Agent Debate Shortlisting — Advocate vs. Skeptic vs. Judge.
LangGraph pipeline with conditional rebuttal round.
Mock mode returns a canned transcript for UI testing without API credits.
"""
import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.services.llm import ask_claude, ask_claude_json, llm_available


class DebateState(TypedDict):
    resume_text: str
    job_description: str
    candidate_name: str
    advocate_case: Optional[str]
    skeptic_case: Optional[str]
    rebuttal: Optional[str]
    verdict: Optional[dict]
    status: Optional[str]


# ── Agent 1: Advocate ────────────────────────────
def advocate_agent(state: DebateState) -> DebateState:
    prompt = f"""You are the ADVOCATE in a hiring debate. Make the strongest possible case
FOR shortlisting this candidate for the job. Cite specific evidence from the resume.
Be persuasive but honest. 4-6 sentences maximum.

JOB DESCRIPTION:
{state['job_description'][:2500]}

CANDIDATE RESUME:
{state['resume_text'][:4000]}"""
    case = ask_claude(prompt, system="You are a skilled hiring advocate.", max_tokens=500)
    return {**state, "advocate_case": case, "status": "advocated"}


# ── Agent 2: Skeptic ─────────────────────────────
def skeptic_agent(state: DebateState) -> DebateState:
    prompt = f"""You are the SKEPTIC in a hiring debate. The Advocate argued:
"{state['advocate_case']}"

Make the strongest case AGAINST shortlisting this candidate: gaps, missing requirements,
risks, weak evidence. Be critical but fair. 4-6 sentences maximum.

JOB DESCRIPTION:
{state['job_description'][:2500]}

CANDIDATE RESUME:
{state['resume_text'][:4000]}"""
    case = ask_claude(prompt, system="You are a rigorous hiring skeptic.", max_tokens=500)
    return {**state, "skeptic_case": case, "status": "challenged"}


# ── Agent 3: Rebuttal (one round) ────────────────
def rebuttal_agent(state: DebateState) -> DebateState:
    prompt = f"""You are the ADVOCATE again. The Skeptic's strongest objection was:
"{state['skeptic_case']}"

Respond to their SINGLE strongest point with evidence from the resume. If a concern
is valid, acknowledge it honestly. 3-4 sentences maximum.

CANDIDATE RESUME:
{state['resume_text'][:4000]}"""
    reb = ask_claude(prompt, system="You are a skilled hiring advocate responding to criticism.", max_tokens=400)
    return {**state, "rebuttal": reb, "status": "rebutted"}


# ── Agent 4: Judge ───────────────────────────────
def judge_agent(state: DebateState) -> DebateState:
    system = "You are an impartial hiring judge. Respond with ONLY valid JSON, no markdown fences."
    prompt = f"""Weigh this hiring debate and deliver a verdict.

ADVOCATE'S CASE: {state['advocate_case']}

SKEPTIC'S CASE: {state['skeptic_case']}

ADVOCATE'S REBUTTAL: {state['rebuttal']}

Return ONLY JSON:
{{"recommendation": "shortlist" or "reject" or "borderline",
  "confidence": 0-100,
  "key_reasons": ["reason 1", "reason 2", "reason 3"]}}"""
    verdict = ask_claude_json(prompt, system=system, max_tokens=400)
    return {**state, "verdict": verdict, "status": "judged"}


# ── Build the graph ──────────────────────────────
def build_debate_workflow():
    graph = StateGraph(DebateState)
    graph.add_node("advocate", advocate_agent)
    graph.add_node("skeptic", skeptic_agent)
    graph.add_node("rebuttal", rebuttal_agent)
    graph.add_node("judge", judge_agent)

    graph.set_entry_point("advocate")
    graph.add_edge("advocate", "skeptic")
    graph.add_edge("skeptic", "rebuttal")
    graph.add_edge("rebuttal", "judge")
    graph.add_edge("judge", END)
    return graph.compile()


debate_workflow = build_debate_workflow()


# ── Mock transcript (UI testing without credits) ─
def mock_debate(candidate_name: str) -> dict:
    return {
        "advocate_case": f"[MOCK] {candidate_name} shows strong alignment with the role: "
                         "relevant technical skills (Python, FastAPI, SQL), demonstrated project "
                         "delivery, and evidence of continuous learning. Their resume shows "
                         "hands-on experience with the exact stack described in the JD.",
        "skeptic_case": "[MOCK] However, the resume lacks quantified impact metrics, shows no "
                        "production-scale experience, and several claimed skills have no "
                        "supporting project context. The JD requires 3+ years; the timeline "
                        "suggests less.",
        "rebuttal": "[MOCK] The experience-length concern is valid, but the depth of the "
                    "portfolio projects — including containerized deployment — demonstrates "
                    "practical maturity beyond years-on-paper.",
        "verdict": {
            "recommendation": "borderline",
            "confidence": 62,
            "key_reasons": [
                "[MOCK] Strong technical stack match with the role",
                "[MOCK] Experience duration below stated requirement",
                "[MOCK] Portfolio depth partially offsets experience gap"
            ]
        }
    }


# ── Main entry point ─────────────────────────────
def run_debate(resume_text: str, job_description: str, candidate_name: str,
               force_mock: bool = False) -> dict:
    """Run the full debate. Uses mock transcript if no API available or force_mock=True."""

    if force_mock or not llm_available:
        result = mock_debate(candidate_name)
        result["is_mock"] = True
        result["pipeline"] = ["advocate", "skeptic", "rebuttal", "judge"]
        return result

    initial: DebateState = {
        "resume_text": resume_text,
        "job_description": job_description,
        "candidate_name": candidate_name,
        "advocate_case": None,
        "skeptic_case": None,
        "rebuttal": None,
        "verdict": None,
        "status": "started"
    }
    final = debate_workflow.invoke(initial)
    return {
        "advocate_case": final["advocate_case"],
        "skeptic_case": final["skeptic_case"],
        "rebuttal": final["rebuttal"],
        "verdict": final["verdict"],
        "is_mock": False,
        "pipeline": ["advocate", "skeptic", "rebuttal", "judge"]
    }