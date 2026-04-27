from fastapi import APIRouter, HTTPException
from app.models.schemas import JobDescription, JobCreateRequest
from app.services.store import save_job, get_job, get_all_jobs

router = APIRouter()


@router.post("/jobs")
async def create_job(request: JobCreateRequest):
    """Create a job posting."""
    job = JobDescription(**request.model_dump())
    jid = save_job(job)
    return {"message": "Job created", "job_id": jid, "job": job}


@router.get("/jobs")
async def list_jobs():
    """List all job postings."""
    store = get_all_jobs()
    return {
        "total": len(store),
        "jobs": [
            {"id": jid, "title": j.title, "required_skills": j.required_skills}
            for jid, j in store.items()
        ]
    }


@router.get("/jobs/{job_id}")
async def get_job_detail(job_id: str):
    """Get details of a specific job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
