from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from app.services.parser import extract_text_from_pdf, parse_resume_with_claude
from app.services.ats import analyze_ats


# ── Shared State passed between agents ──────────
class AgentState(TypedDict):
    file_path: str
    parsed_text: Optional[str]
    parsed_data: Optional[dict]
    ats_result: Optional[dict]
    final_report: Optional[dict]
    status: Optional[str]


# ── Agent 1: Parser Agent ────────────────────────
def parser_agent(state: AgentState) -> AgentState:
    """Extracts text from PDF and parses candidate info"""
    text = extract_text_from_pdf(state["file_path"])
    parsed = parse_resume_with_claude(text)
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


# ── Agent 3: Report Agent ────────────────────────
def report_agent(state: AgentState) -> AgentState:
    """Combines everything into a final report"""
    report = {
        "candidate": state["parsed_data"],
        "ats_analysis": state["ats_result"],
        "pipeline": ["parser_agent", "ats_agent", "report_agent"],
        "status": "completed"
    }
    return {
        **state,
        "final_report": report,
        "status": "completed"
    }


# ── Build the Graph: parser → ats → report ──────
def build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("parser", parser_agent)
    graph.add_node("ats", ats_agent)
    graph.add_node("report", report_agent)

    graph.set_entry_point("parser")
    graph.add_edge("parser", "ats")
    graph.add_edge("ats", "report")
    graph.add_edge("report", END)

    return graph.compile()


talent_workflow = build_workflow()


def run_pipeline(file_path: str) -> dict:
    """Run a resume through the full agent pipeline"""
    initial_state = {
        "file_path": file_path,
        "parsed_text": None,
        "parsed_data": None,
        "ats_result": None,
        "final_report": None,
        "status": "started"
    }
    result = talent_workflow.invoke(initial_state)
    return result["final_report"]