from typing import Optional
from app.models.schemas import ParsedResume, JobDescription
import uuid


# Simple in-memory store (replace with DB in production)
candidates_store: dict[str, ParsedResume] = {}
jobs_store: dict[str, JobDescription] = {}


def save_candidate(parsed: ParsedResume) -> str:
    cid = str(uuid.uuid4())[:8]
    candidates_store[cid] = parsed
    return cid


def get_candidate(cid: str) -> Optional[ParsedResume]:
    return candidates_store.get(cid)


def get_all_candidates() -> dict[str, ParsedResume]:
    return candidates_store


def save_job(job: JobDescription) -> str:
    jid = str(uuid.uuid4())[:8]
    jobs_store[jid] = job
    return jid


def get_job(jid: str) -> Optional[JobDescription]:
    return jobs_store.get(jid)


def get_all_jobs() -> dict[str, JobDescription]:
    return jobs_store
