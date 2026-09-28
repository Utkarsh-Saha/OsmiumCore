import os
import tempfile
import asyncio
from typing import Optional

_whisper_model = None

def _get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        model_name = os.getenv("WHISPER_MODEL", "base")
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model

def _run_whisper_sync(audio_path: str) -> str:
    import torch
    model = _get_model()
    use_fp16 = torch.cuda.is_available()
    result = model.transcribe(audio_path, fp16=use_fp16)
    return result.get("text", "").strip()

async def transcribe_audio(
    user_id: str,
    audio_bytes: bytes,
    file_extension: Optional[str] = ".wav"
) -> str:
    """Transcribe audio using local OpenAI Whisper model.

    Writes the audio bytes to a temporary file, runs Whisper in a thread pool executor,
    and returns the transcribed text.
    """
    if not audio_bytes:
        return ""

    if not file_extension:
        file_extension = ".wav"
    if not file_extension.startswith("."):
        file_extension = f".{file_extension}"

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    try:
        tmp_file.write(audio_bytes)
        tmp_file.flush()
        tmp_path = tmp_file.name
    finally:
        tmp_file.close()

    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, _run_whisper_sync, tmp_path)
        return text
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
