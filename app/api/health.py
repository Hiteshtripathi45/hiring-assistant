from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "llm": "gemini-1.5-flash" if settings.GOOGLE_API_KEY else "gpt-4o-mini" if settings.OPENAI_API_KEY else "not configured",
    }


@router.get("/health/root")
async def root():
    return {
        "message": "🤖 AI Hiring Assistant API",
        "docs": "/docs",
        "health": "/health",
    }
