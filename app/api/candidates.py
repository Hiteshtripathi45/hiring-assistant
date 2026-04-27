from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional

from app.models.schemas import ResumeUploadResponse, RankingResult, CandidateScore
from app.services.resume_service import parse_resume, rank_candidates
from app.services.store import save_candidate, get_all_candidates, get_candidate

router = APIRouter()


@router.post("/candidates/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a candidate resume (PDF or TXT).
    Automatically parses and extracts structured data using AI.
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")

    allowed = {".pdf", ".txt"}
    ext = "." + file.filename.split(".")[-1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type not supported. Use: {allowed}")

    file_bytes = await file.read()

    if len(file_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(400, "File too large. Max 5MB.")

    try:
        parsed = await parse_resume(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to parse resume: {str(e)}")

    candidate_id = save_candidate(parsed)

    return ResumeUploadResponse(
        message="Resume parsed successfully",
        candidate_id=candidate_id,
        parsed_data=parsed,
    )


@router.get("/candidates")
async def list_candidates():
    """List all uploaded candidates."""
    store = get_all_candidates()
    return {
        "total": len(store),
        "candidates": [
            {"id": cid, "name": c.name, "skills": c.skills[:5], "experience_years": c.experience_years}
            for cid, c in store.items()
        ]
    }


@router.get("/candidates/{candidate_id}")
async def get_candidate_detail(candidate_id: str):
    """Get full parsed details of a specific candidate."""
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    return candidate


@router.post("/candidates/rank", response_model=RankingResult)
async def rank_all_candidates(
    job_title: str,
    job_description: str,
    required_skills: str,
    preferred_skills: str = "",
    min_experience_years: float = 0,
):
    """
    Rank all uploaded candidates against a job description.
    
    - required_skills: comma-separated (e.g. "Python,FastAPI,Docker")
    - preferred_skills: comma-separated (optional)
    """
    store = get_all_candidates()
    if not store:
        raise HTTPException(400, "No candidates uploaded yet. Upload resumes first.")

    req_skills = [s.strip() for s in required_skills.split(",") if s.strip()]
    pref_skills = [s.strip() for s in preferred_skills.split(",") if s.strip()]

    candidates = list(store.values())

    try:
        rankings = await rank_candidates(
            candidates=candidates,
            job_title=job_title,
            job_description=job_description,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            min_experience=min_experience_years,
        )
    except Exception as e:
        raise HTTPException(500, f"Ranking failed: {str(e)}")

    scored = [CandidateScore(**r) for r in rankings]
    scored.sort(key=lambda x: x.overall_score, reverse=True)

    top = scored[0] if scored else None

    return RankingResult(
        job_title=job_title,
        total_candidates=len(scored),
        ranked_candidates=scored,
        top_recommendation=f"{top.candidate_name} (Score: {top.overall_score})" if top else "No candidates",
    )
