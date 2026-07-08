import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.chat import ChatSession, ChatMessage
from app.services.rag import answer_question
from app.services.llm import llm_available

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions")
def create_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a new chat conversation"""
    session = ChatSession(user_id=current_user.id, title="New Conversation")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "title": session.title}


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List recruiter's past conversations (newest first)"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()
    return [{"session_id": s.id, "title": s.title, "created_at": str(s.created_at)}
            for s in sessions]


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Load full message history of a conversation"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()

    return {
        "session_id": session.id,
        "title": session.title,
        "messages": [{
            "role": m.role,
            "content": m.content,
            "citations": json.loads(m.citations) if m.citations else []
        } for m in messages]
    }


@router.post("/sessions/{session_id}/message")
def send_message(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask a question; RAG answers, both question and answer are saved."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # Load recruiter's resumes as the knowledge base
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    resume_data = [{
        "id": r.id,
        "candidate_name": r.candidate_name,
        "parsed_text": r.parsed_text,
        "skills_text": r.skills or ""
    } for r in resumes]

    # Load prior history for context
    prior = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    history = [{"role": m.role, "content": m.content} for m in prior]

    # Save the user's question
    db.add(ChatMessage(session_id=session_id, role="user", content=question, citations=None))

    # If this is the first message, set the session title from it
    if not prior:
        session.title = question[:50]

    # Get the RAG answer
    result = answer_question(question, resume_data, history)

    # Save the assistant's answer
    db.add(ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        citations=json.dumps(result["citations"])
    ))
    db.commit()

    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "llm_used": result["llm_used"],
        "session_title": session.title
    }


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation and its messages"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted": session_id}