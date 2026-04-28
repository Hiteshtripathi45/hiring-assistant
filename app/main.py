from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import HTMLResponse
from app.api import candidates, jobs, health
from app.core.config import settings
from fastapi.responses import FileResponse


from fastapi import Request
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Hiring Assistant API starting up...")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title="AI Hiring Assistant",
    description="Agentic AI-powered hiring assistant using LangChain + FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health/root", tags=["Health"])
app.include_router(candidates.router, prefix="/api/v1", tags=["Candidates"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])



@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")