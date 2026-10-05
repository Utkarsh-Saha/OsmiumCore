import sys
import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure Backend root is in sys.path so app modules are always resolved
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

env_path = Path(backend_dir) / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv()

from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import google

from app.core.database import init_db, get_connection
from app.services.memory_service import (
    get_or_create_profile,
    get_recent_conversation_turns,
    log_user_turn,
    search_memories,
)

logger = logging.getLogger("osmium.agent")
logging.basicConfig(level=logging.INFO)

# Pre-flight environment check
if not os.getenv("GOOGLE_API_KEY"):
    logger.warning("GOOGLE_API_KEY is not set in backend environment variables.")

class OsmiumAssistant(Agent):
    def __init__(self, instructions: str = "") -> None:
        base_prompt = (
            "You are OsmiumCore, a composed, intelligent, voice-first desktop AI assistant. "
            "Keep responses concise, clear, and natural for speech output. "
            "You have access to user personalization and conversation memory."
        )
        if instructions:
            base_prompt += f"\n\n{instructions}"
        super().__init__(instructions=base_prompt)

server = AgentServer()

async def _persist_voice_turn(user_id: str, session_id: str, role: str, content: str, room_name: str) -> None:
    """Safely log voice interaction turn into the unified SQLite database."""
    try:
        async with get_connection() as conn:
            await log_user_turn(
                conn,
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                room_name=room_name,
            )
            logger.info(f"Persisted {role} voice turn to DB for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to persist voice turn to DB: {e}", exc_info=True)

@server.rtc_session
async def entrypoint(ctx: JobContext):
    # 1. Ensure SQLite database tables are created
    await init_db()

    # 2. Join the LiveKit RTC room
    await ctx.connect()

    # 3. Identify user and session context
    participant = await ctx.wait_for_participant()
    user_id = participant.identity if participant and participant.identity else "default-user"
    room_name = ctx.room.name or "osmiumcore-default"
    session_id = f"voice-{room_name}-{user_id}"

    # 4. Fetch user profile and relevant memories from unified SQLite store
    context_lines = []
    preferred_voice = "Puck"
    profile = {}
    try:
        async with get_connection() as conn:
            profile = await get_or_create_profile(conn, user_id)
            if profile.get("display_name"):
                context_lines.append(f"User Name: {profile['display_name']}")
            if profile.get("system_prompt_overrides"):
                context_lines.append(f"User Preferences: {profile['system_prompt_overrides']}")
            if profile.get("voice_preference"):
                preferred_voice = profile["voice_preference"]

            # Load recent conversation history across sessions for context continuity
            recent_turns = await get_recent_conversation_turns(conn, session_id, limit=4)
            if recent_turns:
                history_summary = "\n".join([f"- {t['role']}: {t['content']}" for t in recent_turns])
                context_lines.append(f"Recent session history:\n{history_summary}")
    except Exception as e:
        logger.error(f"Error loading user profile/memory for {user_id}: {e}")

    custom_instructions = "\n".join(context_lines)

    # 5. Initialize Gemini Live API realtime model session
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice=preferred_voice,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    )

    # 6. Hook into conversation events to persist every turn into the unified SQLite database
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        try:
            item = getattr(event, "item", None)
            if item is None:
                return
            role = getattr(item, "role", "unknown")
            text = getattr(item, "text_content", "") or getattr(item, "raw_text_content", "")
            if text and text.strip():
                # Map LiveKit roles to standard roles ('user' / 'assistant')
                normalized_role = "user" if role == "user" else "assistant"
                asyncio.create_task(
                    _persist_voice_turn(
                        user_id=user_id,
                        session_id=session_id,
                        role=normalized_role,
                        content=text.strip(),
                        room_name=room_name,
                    )
                )
        except Exception as err:
            logger.error(f"Error handling conversation_item_added: {err}")

    # 7. Start the session in the room
    await session.start(
        agent=OsmiumAssistant(instructions=custom_instructions),
        room=ctx.room,
    )

    # 8. Initial voice greeting when client connects
    greeting = "Greet the user warmly as OsmiumCore and ask how you can assist."
    if profile.get("display_name"):
        greeting = f"Greet {profile['display_name']} warmly by name as OsmiumCore and ask how you can assist."

    await session.generate_reply(instructions=greeting)

if __name__ == "__main__":
    cli.run_app(server)