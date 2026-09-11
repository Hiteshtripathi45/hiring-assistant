from typing import Optional
from app.models.schemas import ParsedResume, JobDescription
import uuid



candidates_store: dict[str, ParsedResume] = {}
jobs_store: dict[str, JobDescription] = {}

resume_text_store: dict[str, str] = {}


review_queue: list[dict] = []


def save_candidate(parsed: ParsedResume, full_text: Optional[str] = None) -> str:
    cid = str(uuid.uuid4())[:8]
    candidates_store[cid] = parsed
    if full_text is not None:
        resume_text_store[cid] = full_text
    return cid


def get_candidate(cid: str) -> Optional[ParsedResume]:
    return candidates_store.get(cid)


def get_all_candidates() -> dict[str, ParsedResume]:
    return candidates_store


def get_candidate_id_by_name(name: str) -> Optional[str]:
    """Look up a candidate id by name (used by agent tools, which only see names)."""
    for cid, c in candidates_store.items():
        if c.name.strip().lower() == name.strip().lower():
            return cid
    return None


def get_full_resume_text(cid: str) -> Optional[str]:
    return resume_text_store.get(cid)


def add_review_flag(candidate_id: str, candidate_name: str, reason: str) -> None:
    review_queue.append({
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "reason": reason,
    })


def get_review_queue() -> list[dict]:
    return review_queue


def save_job(job: JobDescription) -> str:
    jid = str(uuid.uuid4())[:8]
    jobs_store[jid] = job
    return jid


def get_job(jid: str) -> Optional[JobDescription]:
    return jobs_store.get(jid)


def get_all_jobs() -> dict[str, JobDescription]:
    return jobs_store
