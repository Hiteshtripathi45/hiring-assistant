from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional

from app.models.schemas import (
    ResumeUploadResponse, RankingResult, CandidateScore,
    RankAndActResult, CandidateActionResult,
)
from app.services.resume_service import parse_resume, rank_candidates
from app.services.store import (
    save_candidate, get_all_candidates, get_candidate,
    get_candidate_id_by_name, get_review_queue,
)
from app.services.agent_service import qa_review_all
from app.services.notification_service import generate_interview_invite, send_interview_email

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
        parsed, full_text = await parse_resume(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to parse resume: {str(e)}")

    candidate_id = save_candidate(parsed, full_text)

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


@router.post("/candidates/rank/act", response_model=RankAndActResult)
async def rank_and_act(
    job_title: str,
    job_description: str,
    required_skills: str,
    preferred_skills: str = "",
    min_experience_years: float = 0,
):
    """
    Rank candidates, then actually act on the result instead of just
    returning scores:

    1. A QA agent independently reviews each ranking (it can pull the full
       resume text if the ranking's reasoning looks thin, and flags genuine
       inconsistencies for human review instead of trusting the score blindly).
    2. Candidates that pass QA and are scored "Strong Hire" or "Hire" get a
       real .ics interview invite generated, and an interview email sent
       (or dry-run logged if SMTP isn't configured — check the `detail` field).
    3. Candidates the QA agent flagged are NOT auto-scheduled; they're added
       to the review queue (see GET /candidates/review-queue) for a human
       to look at instead.
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

    # Step 1: independent QA pass over every ranking result.
    qa_notes = await qa_review_all([s.model_dump() for s in scored])

    before_queue_size = len(get_review_queue())
    actions: list[CandidateActionResult] = []

    for s in scored:
        cid = get_candidate_id_by_name(s.candidate_name)
        candidate = get_candidate(cid) if cid else None
        qa_note = qa_notes.get(s.candidate_name, "")

        was_flagged = any(
            entry["candidate_name"] == s.candidate_name
            for entry in get_review_queue()[before_queue_size:]
        )

        if was_flagged:
            actions.append(CandidateActionResult(
                candidate_name=s.candidate_name,
                qa_review=qa_note,
                action_taken="flagged_for_review",
                detail={},
            ))
            continue

        if s.recommendation in ("Strong Hire", "Hire"):
            ics_path = generate_interview_invite(s.candidate_name, job_title)
            candidate_email = candidate.email if candidate else None
            send_result = send_interview_email(candidate_email, s.candidate_name, job_title, ics_path)
            actions.append(CandidateActionResult(
                candidate_name=s.candidate_name,
                qa_review=qa_note,
                action_taken="invite_sent" if send_result["status"] == "sent" else "invite_dry_run",
                detail=send_result,
            ))
        else:
            actions.append(CandidateActionResult(
                candidate_name=s.candidate_name,
                qa_review=qa_note,
                action_taken="no_action",
                detail={},
            ))

    return RankAndActResult(
        job_title=job_title,
        total_candidates=len(scored),
        ranked_candidates=scored,
        actions=actions,
        review_queue_size=len(get_review_queue()),
    )


@router.get("/candidates/review-queue")
async def review_queue():
    """List candidates the QA agent flagged for manual human review,
    instead of letting an inconsistent ranking auto-schedule an interview."""
    queue = get_review_queue()
    return {"total": len(queue), "flagged": queue}
