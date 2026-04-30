# 🤖 AI Hiring Assistant

An **agentic AI-powered hiring assistant** built with **FastAPI + LangChain** that automatically parses resumes and ranks candidates against job descriptions using LLMs.

> **Resume-worthy project** — demonstrates: FastAPI, LangChain, LLM integration, async Python, Pydantic, REST API design, AI agents.

---

## 🎯 Features

- 📄 **Resume Parsing** — Upload PDF resumes, AI extracts structured data (skills, experience, education)
- 🏆 **Candidate Ranking** — Rank candidates against any job description with explainable scores
- 🔍 **Skill Gap Analysis** — Shows matched skills, missing skills, and bonus skills per candidate
- ⚡ **Async Processing** — Non-blocking LLM calls with FastAPI async
- 🔌 **Multi-LLM Support** — Works with Gemini (free) or OpenAI
- 📚 **Auto API Docs** — Swagger UI at `/docs`

---

## 🏗️ Architecture

```
User uploads PDF Resume
        ↓
FastAPI receives file (multipart)
        ↓
pdfplumber extracts raw text
        ↓
LangChain prompt → Gemini/GPT-4o-mini
        ↓
LLM returns structured JSON
        ↓
Pydantic validates → ParsedResume model
        ↓
Stored in-memory (or swap with DB)
        ↓
POST /candidates/rank
        ↓
LangChain ranking prompt → LLM
        ↓
Returns scored + ranked candidates
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/ai-hiring-assistant
cd ai-hiring-assistant
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your API key
```

Get a **free** Google Gemini API key at: https://aistudio.google.com/app/apikey

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive API docs.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/candidates/upload` | Upload & parse resume |
| `GET` | `/api/v1/candidates` | List all candidates |
| `GET` | `/api/v1/candidates/{id}` | Get candidate details |
| `POST` | `/api/v1/candidates/rank` | Rank candidates for a job |
| `POST` | `/api/v1/jobs` | Create job posting |
| `GET` | `/api/v1/jobs` | List all jobs |

---

## 💡 Example Usage

### Upload a Resume

```bash
curl -X POST "http://localhost:8000/api/v1/candidates/upload" \
  -F "file=@resume.pdf"
```

**Response:**
```json
{
  "message": "Resume parsed successfully",
  "candidate_id": "a1b2c3d4",
  "parsed_data": {
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "React"],
    "experience_years": 3.5,
    "experience_level": "mid",
    "education": ["B.Tech Computer Science - IIT Delhi"],
    "summary": "Full-stack developer with 3.5 years..."
  }
}
```

### Rank Candidates

```bash
curl -X POST "http://localhost:8000/api/v1/candidates/rank" \
  -G \
  --data-urlencode "job_title=Backend Engineer" \
  --data-urlencode "job_description=We need a backend engineer for our fintech startup" \
  --data-urlencode "required_skills=Python,FastAPI,PostgreSQL,Docker" \
  --data-urlencode "preferred_skills=Redis,Kubernetes" \
  --data-urlencode "min_experience_years=2"
```

**Response:**
```json
{
  "job_title": "Backend Engineer",
  "total_candidates": 3,
  "top_recommendation": "Rahul Sharma (Score: 87.5)",
  "ranked_candidates": [
    {
      "candidate_name": "Rahul Sharma",
      "overall_score": 87.5,
      "skill_match_score": 92.0,
      "experience_score": 80.0,
      "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
      "missing_skills": [],
      "bonus_skills": ["Redis"],
      "reasoning": "Strong match with all required skills. 3.5 years meets minimum requirement...",
      "recommendation": "Strong Hire"
    }
  ]
}
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | REST API framework |
| **LangChain** | LLM orchestration, prompt management |
| **Gemini 1.5 Flash** | LLM (free tier available) |
| **Pydantic** | Data validation & serialization |
| **pdfplumber** | PDF text extraction |
| **uvicorn** | ASGI server |

---

## 📁 Project Structure

```
hiring-assistant/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   └── config.py        # Settings & env vars
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── api/
│   │   ├── candidates.py    # Candidate endpoints
│   │   ├── jobs.py          # Job endpoints
│   │   └── health.py        # Health check
│   └── services/
│       ├── resume_service.py # LangChain + LLM logic
│       └── store.py          # In-memory data store
├── requirements.txt
├── .env.example
└── README.md
```


PRs welcome! Built by hitesh tripathi — https://www.linkedin.com/in/hitesh-tripathi-167262402/?skipRedirect=true
