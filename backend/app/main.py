import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.core.database import Base, engine
from app.api.routes import auth, resume, job, report, debate
from app.models import debate as debate_model  # ensures debates table is created


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TalentAI Recruiter",
    description="AI-Powered Recruitment Platform — resume parsing, ATS scoring, FAISS semantic matching, LangGraph agents, PDF reports",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-detect frontend location (works locally AND in Docker)
FRONTEND_DIR = "frontend" if os.path.exists("frontend") else "../frontend"

app.mount("/static", StaticFiles(directory=f"{FRONTEND_DIR}/static"), name="static")
templates = Jinja2Templates(directory=f"{FRONTEND_DIR}/templates")

app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(job.router)
app.include_router(report.router)
app.include_router(debate.router)

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "TalentAI is running 🚀"}