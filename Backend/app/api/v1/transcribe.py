import os
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from app.services.transcription_service import transcribe_audio
from app.services.memory_service import log_user_turn
from app.core.database import get_connection

router = APIRouter()

@router.post("/transcribe", tags=["Transcription"])
async def transcribe(
    user_id: str = Form(..., description="Unique user identity"),
    session_id: Optional[str] = Form(None, description="Optional conversation session ID"),
    audio: UploadFile = File(..., description="Audio recording file (wav, mp3, webm, m4a, etc.)")
):
    """Accept an audio file, run Whisper transcription, persist the conversation turn to memory DB, and return the text."""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required")

    actual_session_id = session_id.strip() if session_id and session_id.strip() else f"transcribe-{user_id}"

    try:
        audio_bytes = await audio.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded audio file: {e}")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    file_ext = ".wav"
    if audio.filename and "." in audio.filename:
        file_ext = os.path.splitext(audio.filename)[1]

    try:
        text = await transcribe_audio(user_id=user_id, audio_bytes=audio_bytes, file_extension=file_ext)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    if text:
        async with get_connection() as conn:
            await log_user_turn(
                conn=conn,
                user_id=user_id,
                session_id=actual_session_id,
                role="user",
                content=text
            )

    return {
        "text": text,
        "user_id": user_id,
        "session_id": actual_session_id
    }
