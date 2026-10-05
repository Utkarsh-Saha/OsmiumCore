import pytest
import asyncio
from app.core.database import init_db, get_connection
from app.services.memory_service import (
    get_or_create_profile,
    update_profile,
    log_user_turn,
    get_recent_conversation_turns,
)
from agent.main import _persist_voice_turn

@pytest.mark.asyncio
async def test_unified_database_voice_and_text():
    # 1. Initialize schema in the shared SQLite database
    await init_db()

    user_id = "test_unified_user"
    text_session_id = f"session-{user_id}"
    voice_session_id = f"voice-osmiumcore-default-{user_id}"

    async with get_connection() as conn:
        # Create and customize user profile
        await update_profile(
            conn,
            user_id=user_id,
            display_name="Alex Unified",
            voice_preference="Aoede",
            system_prompt_overrides="Always prioritize concise bullet points."
        )

        # 2. Log a text chat turn
        await log_user_turn(
            conn,
            user_id=user_id,
            session_id=text_session_id,
            role="user",
            content="Hello from text chat!"
        )
        await log_user_turn(
            conn,
            user_id=user_id,
            session_id=text_session_id,
            role="assistant",
            content="Hello Alex, I am Osmium text assistant."
        )

    # 3. Simulate LiveKit Voice Agent persisting a voice turn into the same DB
    await _persist_voice_turn(
        user_id=user_id,
        session_id=voice_session_id,
        role="user",
        content="Hello from real-time voice!",
        room_name="osmiumcore-default"
    )
    await _persist_voice_turn(
        user_id=user_id,
        session_id=voice_session_id,
        role="assistant",
        content="Greetings Alex, I heard you via voice!",
        room_name="osmiumcore-default"
    )

    # 4. Verify both voice and text turns coexist in the unified database
    async with get_connection() as conn:
        profile = await get_or_create_profile(conn, user_id)
        assert profile["display_name"] == "Alex Unified"
        assert profile["voice_preference"] == "Aoede"

        text_turns = await get_recent_conversation_turns(conn, text_session_id, limit=10)
        assert len(text_turns) >= 2
        assert text_turns[0]["content"] == "Hello from text chat!"
        assert text_turns[1]["content"] == "Hello Alex, I am Osmium text assistant."

        voice_turns = await get_recent_conversation_turns(conn, voice_session_id, limit=10)
        assert len(voice_turns) >= 2
        assert voice_turns[0]["content"] == "Hello from real-time voice!"
        assert voice_turns[1]["content"] == "Greetings Alex, I heard you via voice!"
