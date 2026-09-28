import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure Backend directory is in sys.path so 'app....' works regardless of where the command is launched
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from app.core.database import init_db
from app.api.v1 import token, transcribe, message

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite schema on startup
    await init_db()
    yield

app = FastAPI(
    title="OsmiumCore Backend",
    version="0.1.0",
    description="Backend API services for OsmiumCore: Authentication, Long-Term Memory, Whisper STT Transcription & Messaging.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(token.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(transcribe.router, prefix="/api/v1", tags=["Transcription"])
app.include_router(message.router, prefix="/api/v1", tags=["Messaging"])

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "osmiumcore-backend"}