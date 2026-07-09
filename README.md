<div align="center">

# 🎯 TalentAI Recruiter

**An agentic AI recruitment platform with adversarial candidate evaluation, RAG-based talent search, and LLM-powered fraud detection.**

![CI](https://github.com/Saloni248694/TalentAI-Recruiter/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-purple)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Tests](https://img.shields.io/badge/tests-28%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## 📖 Overview

**TalentAI Recruiter** is a full-stack, AI-powered recruitment platform that goes beyond conventional Applicant Tracking Systems. Recruiters upload resumes and job descriptions, and the platform parses, scores, matches, and evaluates candidates using a multi-agent AI pipeline.

Unlike mainstream ATS products, TalentAI ships several features that **do not exist in today's recruitment tools**:

- ⚖️ **Adversarial multi-agent evaluation** — an Advocate, a Skeptic, and a Judge debate each candidate before a verdict
- 💬 **RAG-based conversational search** — ask natural-language questions about your talent pool and get cited answers
- 🎛️ **Interactive requirement-elasticity simulation** — toggle job requirements and watch the candidate pool re-rank live
- 🔍 **Resume consistency auditing** — detect timeline contradictions, inflated experience, and unsupported skill claims

Every AI feature is built with **graceful degradation**: if the LLM API is unavailable, the platform automatically falls back to deterministic heuristics — zero downtime, no crashes.

---

## 📸 Screenshots

> _Replace these placeholders with your actual screenshots. Create a `docs/screenshots/` folder in the repo, drop your PNGs in, and update the paths below._

| Dashboard | AI Debate |
|:---:|:---:|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Debate](docs/screenshots/debate.png) |

| What-If Simulator | RAG Chat |
|:---:|:---:|
| ![Simulator](docs/screenshots/simulator.png) | ![Chat](docs/screenshots/chat.png) |

**How to add screenshots:**
```bash
# From your project root
mkdir docs\screenshots
# Take screenshots of each feature (Windows: Win + Shift + S), save them as:
#   dashboard.png, debate.png, simulator.png, chat.png
# into docs\screenshots\, then:
git add docs/screenshots
git commit -m "Add project screenshots"
git push
```

---

## ✨ Features

### GenAI Core
- **AI Resume Parsing** — Claude-powered extraction of name, contact, skills, experience, and education, with an automatic regex-heuristic fallback
- **AI Resume Optimizer** — rewrites weak bullet points and generates a tailored professional summary
- **ATS Scoring Engine** — keyword, format, and experience scoring with actionable feedback

### Agentic AI
- **4-Agent LangGraph Pipeline** — Parser → ATS → Matching → Report agents orchestrated as a state graph
- **Multi-Agent Debate Shortlisting** — Advocate / Skeptic / Rebuttal / Judge debate architecture with conditional edges and persisted structured verdicts
- **Semantic Candidate Matching** — FAISS vector search over BGE/MiniLM embeddings

### Retrieval + Explainability
- **RAG Chat over Talent Pool** — chunked retrieval, cited answers, hallucination guardrails, and persistent multi-session chat history with context-aware follow-ups
- **JD What-If Simulator** — requirement chips, live FAISS re-ranking, and delta analytics (pool size, average match, biggest movers)

### Trust & Safety
- **Resume Consistency Auditor** — timeline overlap detection, employment-gap analysis, experience-inflation checks, and title-velocity flags, with an optional LLM audit pass

### Engineering
- **JWT Authentication** — bcrypt-hashed passwords, per-user data isolation
- **PDF Reports** — ranked candidate reports and a full contact directory export
- **28 Automated Tests** — pytest suite with mocked LLM clients (CI runs free, no API cost)
- **GitHub Actions CI/CD** — tests + Docker build on every push
- **Dockerized** — full `docker-compose` deployment (API + PostgreSQL + Redis)

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic |
| **AI / ML** | Anthropic Claude API, LangGraph, sentence-transformers (all-MiniLM-L6-v2), FAISS |
| **Database** | PostgreSQL |
| **Cache** | Redis (optional, fault-tolerant) |
| **Parsing** | PyMuPDF4LLM, python-dateutil |
| **Reports** | ReportLab |
| **Auth** | JWT (python-jose), bcrypt (passlib) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Testing** | pytest, pytest-asyncio, httpx |
| **DevOps** | Docker, Docker Compose, GitHub Actions |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vanilla JS)                  │
│   Resumes · Jobs · Matches · Reports · Simulator · Ask AI     │
└───────────────────────────────┬─────────────────────────────┘
                                 │ REST / JWT
┌───────────────────────────────▼─────────────────────────────┐
│                         FastAPI Backend                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Auth    │  │  Resume  │  │   Job    │  │  Debate/Chat  │  │
│  │  Routes  │  │  Routes  │  │  Routes  │  │    Routes     │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└───────┬───────────────┬───────────────┬──────────────┬──────┘
        │               │               │              │
┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  LangGraph   │ │   Services  │ │    FAISS    │ │   Claude   │
│ 4-agent +    │ │ parser/ats/ │ │  Vector     │ │  API (with │
│ debate graph │ │ auditor/rag │ │  Search     │ │  fallback) │
└──────────────┘ └─────────────┘ └─────────────┘ └────────────┘
        │               │               │
┌───────▼───────────────▼───────────────▼─────────────────────┐
│              PostgreSQL  ·  Redis (optional cache)            │
└──────────────────────────────────────────────────────────────┘
```

**Graceful degradation:** every Claude call is wrapped so that on any API failure (no credits, network, rate limit) the feature falls back to a deterministic path — regex parsing, rule-based auditing, retrieval-only chat answers, or a mock debate transcript. The application never crashes on LLM unavailability.

---

## 🔌 API Endpoints

<details>
<summary><b>Authentication</b></summary>

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a recruiter |
| POST | `/auth/login` | Login, returns JWT |
</details>

<details>
<summary><b>Resumes</b></summary>

| Method | Endpoint | Description |
|---|---|---|
| POST | `/resumes/upload` | Upload & parse resumes |
| GET | `/resumes/` | List (with search/filter/sort) |
| GET | `/resumes/{id}` | Resume detail |
| POST | `/resumes/{id}/reanalyze` | Re-run 4-agent pipeline |
| POST | `/resumes/{id}/optimize` | AI resume optimizer |
| POST | `/resumes/{id}/audit` | Consistency / fraud audit |
| DELETE | `/resumes/{id}` | Delete resume |
</details>

<details>
<summary><b>Jobs & Simulator</b></summary>

| Method | Endpoint | Description |
|---|---|---|
| POST | `/jobs/` | Create job description |
| GET | `/jobs/` | List jobs |
| POST | `/jobs/{id}/match` | Match candidates (FAISS) |
| GET | `/jobs/{id}/requirements` | Extract requirement chips |
| POST | `/jobs/{id}/simulate` | What-if requirement simulation |
</details>

<details>
<summary><b>Debate, Chat & Reports</b></summary>

| Method | Endpoint | Description |
|---|---|---|
| POST | `/debate/{resume_id}/{job_id}` | Run multi-agent debate |
| GET | `/debate/history` | Past debates |
| POST | `/chat/sessions` | New chat session |
| GET | `/chat/sessions` | List conversations |
| POST | `/chat/sessions/{id}/message` | Ask a question (RAG) |
| DELETE | `/chat/sessions/{id}` | Delete conversation |
| GET | `/reports/{job_id}/pdf` | Ranked candidate PDF |
| GET | `/reports/contacts/pdf` | Contact directory PDF |
</details>

Full interactive API docs are available at `http://localhost:8000/docs` (Swagger UI) when the server is running.

---

## 📁 Project Structure

```
TalentAI/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── workflow.py        # 4-agent LangGraph pipeline
│   │   │   └── debate.py          # Advocate/Skeptic/Judge debate graph
│   │   ├── api/routes/
│   │   │   ├── auth.py  resume.py  job.py
│   │   │   ├── report.py  debate.py  chat.py
│   │   ├── core/
│   │   │   ├── config.py  database.py  security.py
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic schemas
│   │   └── services/
│   │       ├── llm.py             # Claude wrapper + fallback
│   │       ├── parser.py  ats.py  matcher.py
│   │       ├── auditor.py         # Consistency auditing
│   │       ├── simulator.py       # What-if simulation
│   │       ├── rag.py             # RAG retrieval + synthesis
│   │       ├── report.py  cache.py
│   ├── tests/                     # 28 pytest tests
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── templates/                 # index.html, dashboard.html
│   └── static/                    # css/, js/
├── .github/workflows/ci.yml       # GitHub Actions CI
├── docker-compose.yml
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11
- PostgreSQL 14+
- (Optional) Docker & Docker Compose
- (Optional) An Anthropic Claude API key — the app runs without it via fallbacks

### Local Setup (Windows)

**1. Clone the repository**
```bash
git clone https://github.com/Saloni248694/TalentAI-Recruiter.git
cd TalentAI-Recruiter
```

**2. Create the PostgreSQL database**
```sql
CREATE DATABASE talentai;
```

**3. Configure environment**
```bash
cd backend
copy .env.example .env
```
Then edit `.env` with your values:
```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/talentai
SECRET_KEY=your-secret-key-here
CLAUDE_API_KEY=sk-ant-your-key-here   # optional
```

**4. Install dependencies**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**5. Run the server**
```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser. 🎉

> **Offline mode:** if running with no internet (using the cached embedding model), set `set TALENTAI_OFFLINE=1` before starting the server.

### Docker Setup

```bash
# Sync frontend into the backend build context
xcopy frontend backend\frontend /E /I /Y

# Build and run
docker-compose up --build
```

The app will be available at **http://localhost:8000**.

---

## 🧪 Testing

```bash
cd backend
venv\Scripts\activate
pytest
```

The suite contains **28 tests** covering the ATS engine, consistency auditor timeline logic, embedding math, parser fallback, authentication, and the debate pipeline. Claude clients are **mocked**, so tests run without any API cost — this is why CI runs for free on every push.

```
======================= 28 passed in ~50s =======================
```

---

## 🔄 CI/CD

Every push and pull request to `main` triggers the [GitHub Actions pipeline](.github/workflows/ci.yml):

1. **Test job** — installs dependencies, runs the full pytest suite (LLM mocked, SQLite test DB, no secrets)
2. **Docker-build job** — verifies the backend Docker image builds successfully

The status badge at the top of this README reflects the latest run.

---

## 🗺️ Roadmap

- [ ] Cloud deployment (AWS / GCP) with a live demo link
- [ ] Hybrid retrieval (BM25 + vector) with a cross-encoder re-ranker
- [ ] PII redaction / blind-screening guardrails
- [ ] Talent-pool rediscovery agent (proactive re-matching of past candidates)
- [ ] Preference-learning ranker from recruiter feedback

---

## 🤝 Contributing

This is a portfolio project, but suggestions and issues are welcome. Feel free to open an issue or fork the repo.

---

## 📝 License

Released under the MIT License.

---

<div align="center">

**Built with FastAPI, LangGraph, FAISS, and Claude** — demonstrating agentic AI, RAG, and production-grade engineering practices.

</div>
