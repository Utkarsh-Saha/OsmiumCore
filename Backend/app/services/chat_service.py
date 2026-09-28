import os
import asyncio
from pathlib import Path
from typing import Optional, List
import aiosqlite
from dotenv import load_dotenv

from app.services.memory_service import (
    get_or_create_profile,
    search_memories,
    get_recent_conversation_turns,
    log_user_turn,
)

# Ensure Backend/.env is explicitly loaded
env_backend = Path(__file__).resolve().parent.parent.parent / ".env"
if env_backend.exists():
    load_dotenv(dotenv_path=env_backend, override=True)
else:
    load_dotenv()

SYSTEM_PROMPT = (
    "You are OsmiumCore, an intelligent, composed, and helpful desktop AI assistant. "
    "Provide clear, direct, and thoughtful answers. You have access to user personalization "
    "and conversation memory."
)

async def generate_chat_reply(
    conn: aiosqlite.Connection,
    user_id: str,
    session_id: str,
    user_message: str
) -> str:
    """Generate an assistant reply using Gemini (or local Ollama / fallback),
    injecting personalization and long-term memory context, and logging both turns in the SQLite database.
    """
    # 1. Log the user's turn
    await log_user_turn(conn, user_id=user_id, session_id=session_id, role="user", content=user_message)

    # 2. Gather context
    profile = await get_or_create_profile(conn, user_id)
    recent_turns = await get_recent_conversation_turns(conn, session_id, limit=6)

    # Search relevant memories based on words in the query
    memories = []
    try:
        clean_words = [w for w in user_message.split() if len(w) > 3]
        if clean_words:
            query = " OR ".join(clean_words[:4])
            memories = await search_memories(conn, user_id, query, limit=3)
    except Exception:
        memories = []

    # Format context block
    context_lines = []
    if profile.get("display_name"):
        context_lines.append(f"User Name: {profile['display_name']}")
    if profile.get("system_prompt_overrides"):
        context_lines.append(f"User Preferences: {profile['system_prompt_overrides']}")
    if memories:
        context_lines.append("Relevant memories:")
        for m in memories:
            context_lines.append(f"- [{m.get('category', 'general')}] {m.get('content')}")

    context_str = "\n".join(context_lines)

    # Refresh env vars from .env if needed
    if env_backend.exists():
        load_dotenv(dotenv_path=env_backend, override=False)

    google_api_key = os.getenv("GOOGLE_API_KEY")

    reply_text = ""
    if google_api_key and google_api_key.strip() and google_api_key != "your_gemini_api_key_here":
        try:
            loop = asyncio.get_running_loop()
            reply_text = await loop.run_in_executor(
                None,
                _generate_gemini_reply,
                google_api_key,
                user_message,
                recent_turns,
                context_str
            )
        except Exception as e:
            reply_text = f"I encountered an issue generating a reply via Gemini: {e}"
    else:
        # Fallback intelligent response when GOOGLE_API_KEY is not configured
        reply_text = (
            f"Hello! I received your message: \"{user_message}\". "
            "To enable live Gemini AI intelligence, please set your GOOGLE_API_KEY in Backend/.env."
        )

    # 3. Log assistant turn
    await log_user_turn(conn, user_id=user_id, session_id=session_id, role="assistant", content=reply_text)

    return reply_text

def _generate_gemini_reply(api_key: str, message: str, turns: list, context_str: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    system_instruction = SYSTEM_PROMPT
    if context_str:
        system_instruction += f"\n\nPersonalization Context:\n{context_str}"

    # Build conversation contents
    contents = []
    for turn in turns[:-1]:  # exclude the last turn since we send it as current query
        role = "user" if turn["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])]))

    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    # Try preferred Gemini models in priority order
    configured_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    candidate_models = [configured_model, "gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest"]
    # Deduplicate while preserving order
    models_to_try = list(dict.fromkeys(candidate_models))

    last_err = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise last_err
    return "I couldn't generate a text response."
