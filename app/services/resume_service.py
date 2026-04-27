import io
import uuid
import json
import re
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.models.schemas import ParsedResume
from app.core.config import settings


RESUME_PARSE_PROMPT = """You are an expert HR assistant that extracts structured information from resumes.

Extract the following information from the resume text below and return ONLY valid JSON.

Resume Text:
{resume_text}

Return a JSON object with these exact fields:
{{
    "name": "Full name of the candidate",
    "email": "email address or null",
    "phone": "phone number or null", 
    "skills": ["list", "of", "all", "technical", "and", "soft", "skills"],
    "experience_years": 0.0,
    "education": ["degree and institution"],
    "previous_companies": ["company names"],
    "summary": "2-3 sentence professional summary",
    "experience_level": "junior|mid|senior|lead"
}}

Rules:
- experience_level: junior (0-2 yrs), mid (2-5 yrs), senior (5-10 yrs), lead (10+ yrs)
- skills must be specific technologies, frameworks, tools, or competencies
- Return ONLY the JSON, no markdown, no explanation
"""

RANKING_PROMPT = """You are a senior technical recruiter ranking candidates for a job opening.

Job Title: {job_title}
Job Description: {job_description}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Minimum Experience: {min_experience} years

Candidates to evaluate:
{candidates_data}

For each candidate, provide a structured evaluation. Return ONLY valid JSON array:
[
  {{
    "candidate_name": "name",
    "overall_score": 85.0,
    "skill_match_score": 90.0,
    "experience_score": 80.0,
    "matched_skills": ["skills they have that are required"],
    "missing_skills": ["required skills they lack"],
    "bonus_skills": ["preferred skills they have"],
    "reasoning": "2-3 sentence explanation of score",
    "recommendation": "Strong Hire|Hire|Maybe|Reject"
  }}
]

Scoring:
- overall_score = 60% skill_match + 40% experience_score
- skill_match_score: % of required skills matched (0-100)
- experience_score: based on years relative to requirement (0-100)
- Sort by overall_score descending
- Return ONLY the JSON array, no markdown
"""


def get_llm():
    """Get the best available LLM."""
    if settings.GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
    elif settings.OPENAI_API_KEY:
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
    else:
        raise ValueError("No API key found. Set GOOGLE_API_KEY or OPENAI_API_KEY in .env")


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text.strip()
    except ImportError:
        # Fallback: try PyMuPDF
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
        except ImportError:
            raise ImportError("Install pdfplumber or PyMuPDF: pip install pdfplumber")


def clean_json_response(text: str) -> str:
    """Strip markdown fences from LLM response."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


async def parse_resume(file_bytes: bytes, filename: str) -> ParsedResume:
    """Parse resume PDF using LangChain + LLM."""
    
    # Extract raw text
    if filename.lower().endswith(".pdf"):
        raw_text = await extract_text_from_pdf(file_bytes)
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    if not raw_text or len(raw_text) < 50:
        raise ValueError("Could not extract meaningful text from the resume file.")

    # Build LangChain chain
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(RESUME_PARSE_PROMPT)
    chain = prompt | llm

    response = await chain.ainvoke({"resume_text": raw_text[:6000]})
    
    # Parse JSON response
    content = response.content if hasattr(response, "content") else str(response)
    content = clean_json_response(content)
    
    data = json.loads(content)
    data["raw_text"] = raw_text[:1000]  # Store first 1000 chars

    return ParsedResume(**data)


async def rank_candidates(
    candidates: list[ParsedResume],
    job_title: str,
    job_description: str,
    required_skills: list[str],
    preferred_skills: list[str],
    min_experience: float,
) -> list[dict]:
    """Rank candidates against a job description using LangChain."""
    
    if not candidates:
        return []

    candidates_data = json.dumps([
        {
            "name": c.name,
            "skills": c.skills,
            "experience_years": c.experience_years,
            "education": c.education,
            "summary": c.summary,
            "experience_level": c.experience_level,
        }
        for c in candidates
    ], indent=2)

    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(RANKING_PROMPT)
    chain = prompt | llm

    response = await chain.ainvoke({
        "job_title": job_title,
        "job_description": job_description,
        "required_skills": ", ".join(required_skills),
        "preferred_skills": ", ".join(preferred_skills) if preferred_skills else "None",
        "min_experience": min_experience,
        "candidates_data": candidates_data,
    })

    content = response.content if hasattr(response, "content") else str(response)
    content = clean_json_response(content)

    return json.loads(content)
