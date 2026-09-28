import pytest
import io
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, get_connection

@pytest.mark.asyncio
async def test_transcribe_endpoint():
    await init_db()

    # Mock transcribe_audio to avoid requiring downloading Whisper weights in quick unit test
    with patch("app.api.v1.transcribe.transcribe_audio", return_value="Turn on the living room lights."):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            fake_audio = io.BytesIO(b"RIFFdummywavdata")
            files = {"audio": ("test.wav", fake_audio, "audio/wav")}
            data = {"user_id": "test_user_stt", "session_id": "test_session_stt"}

            response = await ac.post("/api/v1/transcribe", data=data, files=files)
            assert response.status_code == 200
            res = response.json()
            assert res["text"] == "Turn on the living room lights."
            assert res["user_id"] == "test_user_stt"
            assert res["session_id"] == "test_session_stt"

            # Verify persisted into DB
            async with get_connection() as conn:
                async with conn.execute(
                    "SELECT role, content FROM conversation_turns WHERE session_id = ?",
                    ("test_session_stt",)
                ) as cur:
                    rows = await cur.fetchall()
                    assert len(rows) >= 1
                    assert rows[-1][0] == "user"
                    assert rows[-1][1] == "Turn on the living room lights."
