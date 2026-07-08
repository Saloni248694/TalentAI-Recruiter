from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from app.services.parser import extract_text_from_pdf, parse_resume_with_claude
from app.services.ats import analyze_ats
from app.services.matcher import get_embedding, search_candidates
import os


# ── Shared State passed between all 4 agents ────
class AgentState(TypedDict):
    file_path: str
    job_description: Optional[str]      # optional matching context
    parsed_text: Optional[str]
    parsed_data: Optional[dict]
    ats_result: Optional[dict]
    match_result: Optional[dict]
    final_report: Optional[dict]
    status: Optional[str]


# ── Agent 1: Parser Agent ────────────────────────
def parser_agent(state: AgentState) -> AgentState:
    """Extracts text from PDF and parses candidate info"""
    text = extract_text_from_pdf(state["file_path"])
    parsed = parse_resume_with_claude(text, filename=os.path.basename(state["file_path"]))
    return {
        **state,
        "parsed_text": text,
        "parsed_data": parsed,
        "status": "parsed"
    }


# ── Agent 2: ATS Agent ───────────────────────────
def ats_agent(state: AgentState) -> AgentState:
    """Analyzes resume for ATS compatibility"""
    ats = analyze_ats(state["parsed_text"])
    return {
        **state,
        "ats_result": ats,
        "status": "ats_analyzed"
    }


# ── Agent 3: Matching Agent ──────────────────────
def matching_agent(state: AgentState) -> AgentState:
    """Computes semantic similarity between this resume and a job description.
    If no job description provided, reports readiness of the embedding only."""
    job_desc = state.get("job_description")

    if job_desc:
        # Direct pairwise similarity: embed both, compare
        import numpy as np
        resume_vec = get_embedding(state["parsed_text"][:2000])
        job_vec = get_embedding(job_desc[:2000])
        # Cosine similarity → percentage
        cos = float(
            np.dot(resume_vec, job_vec) /
            (np.linalg.norm(resume_vec) * np.linalg.norm(job_vec))
        )
        match_score = round(max(0.0, cos) * 100, 2)
        match_result = {
            "job_matched": True,
            "match_score": match_score,
            "method": "cosine_similarity (all-MiniLM-L6-v2)"
        }
    else:
        match_result = {
            "job_matched": False,
            "match_score": None,
            "method": "no job description provided — embedding verified only",
            "embedding_dims": len(get_embedding(state["parsed_text"][:500]))
        }

    return {
        **state,
        "match_result": match_result,
        "status": "matched"
    }


# ── Agent 4: Report Agent ────────────────────────
def report_agent(state: AgentState) -> AgentState:
    """Combines all agent outputs into a final report"""
    report = {
        "candidate": state["parsed_data"],
        "ats_analysis": state["ats_result"],
        "matching": state["match_result"],
        "pipeline": ["parser_agent", "ats_agent", "matching_agent", "report_agent"],
        "status": "completed"
    }
    return {
        **state,
        "final_report": report,
        "status": "completed"
    }


# ── Build Graph: parser → ats → matching → report ──
def build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("parser", parser_agent)
    graph.add_node("ats", ats_agent)
    graph.add_node("matching", matching_agent)
    graph.add_node("report", report_agent)

    graph.set_entry_point("parser")
    graph.add_edge("parser", "ats")
    graph.add_edge("ats", "matching")
    graph.add_edge("matching", "report")
    graph.add_edge("report", END)

    return graph.compile()


talent_workflow = build_workflow()


def run_pipeline(file_path: str, job_description: str = None) -> dict:
    """Run a resume through the full 4-agent pipeline"""
    initial_state = {
        "file_path": file_path,
        "job_description": job_description,
        "parsed_text": None,
        "parsed_data": None,
        "ats_result": None,
        "match_result": None,
        "final_report": None,
        "status": "started"
    }
    result = talent_workflow.invoke(initial_state)
    return result["final_report"]