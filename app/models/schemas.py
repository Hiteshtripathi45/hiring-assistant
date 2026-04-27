from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ExperienceLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class ParsedResume(BaseModel):
    name: str = Field(description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    skills: list[str] = Field(default_factory=list, description="Technical and soft skills")
    experience_years: float = Field(0, description="Total years of experience")
    education: list[str] = Field(default_factory=list, description="Education qualifications")
    previous_companies: list[str] = Field(default_factory=list, description="Previous employers")
    summary: str = Field("", description="Professional summary")
    experience_level: ExperienceLevel = Field(ExperienceLevel.JUNIOR)
    raw_text: str = Field("", description="Raw extracted text")


class JobDescription(BaseModel):
    title: str
    required_skills: list[str]
    preferred_skills: list[str] = []
    min_experience_years: float = 0
    description: str


class CandidateScore(BaseModel):
    candidate_name: str
    overall_score: float = Field(ge=0, le=100)
    skill_match_score: float = Field(ge=0, le=100)
    experience_score: float = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    bonus_skills: list[str]
    reasoning: str
    recommendation: str


class RankingResult(BaseModel):
    job_title: str
    total_candidates: int
    ranked_candidates: list[CandidateScore]
    top_recommendation: str


class ResumeUploadResponse(BaseModel):
    message: str
    candidate_id: str
    parsed_data: ParsedResume


class JobCreateRequest(BaseModel):
    title: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str] = []
    min_experience_years: float = 0
