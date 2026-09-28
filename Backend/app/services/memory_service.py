import os
from datetime import datetime
from typing import List, Optional
import aiosqlite

# Helper to get current timestamp string
def now() -> str:
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'

# ---------------------------------------------------------------------
# Profile operations
# ---------------------------------------------------------------------
async def get_or_create_profile(conn: aiosqlite.Connection, user_id: str) -> dict:
    # Try to fetch existing profile
    async with conn.execute("SELECT user_id, display_name, voice_preference, system_prompt_overrides FROM user_profiles WHERE user_id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
        if row:
            return {
                "user_id": row[0],
                "display_name": row[1],
                "voice_preference": row[2],
                "system_prompt_overrides": row[3],
            }
    # If not found, create a minimal default profile
    await conn.execute(
        "INSERT INTO user_profiles (user_id, created_at, updated_at) VALUES (?, ?, ?)",
        (user_id, now(), now()),
    )
    await conn.commit()
    return {"user_id": user_id, "display_name": None, "voice_preference": None, "system_prompt_overrides": None}

async def update_profile(conn: aiosqlite.Connection, user_id: str, display_name: Optional[str] = None,
                         voice_preference: Optional[str] = None, system_prompt_overrides: Optional[str] = None) -> None:
    fields = []
    values = []
    if display_name is not None:
        fields.append("display_name = ?")
        values.append(display_name)
    if voice_preference is not None:
        fields.append("voice_preference = ?")
        values.append(voice_preference)
    if system_prompt_overrides is not None:
        fields.append("system_prompt_overrides = ?")
        values.append(system_prompt_overrides)
    if not fields:
        return
    values.extend([now(), user_id])
    set_clause = ", ".join(fields) + ", updated_at = ?"
    sql = f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?"
    await conn.execute(sql, tuple(values))
    await conn.commit()

# ---------------------------------------------------------------------
# Memory operations
# ---------------------------------------------------------------------
async def add_memory(conn: aiosqlite.Connection, user_id: str, category: str, content: str, importance: int = 0) -> int:
    cur = await conn.execute(
        "INSERT INTO memories (user_id, category, content, importance, created_at, last_accessed_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, category, content, importance, now(), now()),
    )
    mem_id = cur.lastrowid
    # Also insert into FTS table for searchability
    await conn.execute("INSERT INTO memories_fts(rowid, content) VALUES (?, ?)", (mem_id, content))
    await conn.commit()
    return mem_id

async def delete_memory(conn: aiosqlite.Connection, user_id: str, memory_id: int) -> None:
    await conn.execute("DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
    await conn.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
    await conn.commit()

async def search_memories(conn: aiosqlite.Connection, user_id: str, query: str, limit: int = 10) -> List[dict]:
    # Use FTS5 MATCH operator for full‑text search
    sql = """
        SELECT m.id, m.category, m.content, m.importance, m.created_at
        FROM memories_fts f
        JOIN memories m ON m.id = f.rowid
        WHERE f.content MATCH ? AND m.user_id = ?
        ORDER BY rank
        LIMIT ?
    """
    async with conn.execute(sql, (query, user_id, limit)) as cur:
        rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "category": r[1],
                "content": r[2],
                "importance": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]

# ---------------------------------------------------------------------
# Session & turn logging
# ---------------------------------------------------------------------
async def create_session_log(conn: aiosqlite.Connection, session_id: str, user_id: str, room_name: str, summary: str) -> None:
    await conn.execute(
        "INSERT INTO session_logs (session_id, user_id, room_name, summary, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, room_name, summary, now()),
    )
    await conn.commit()

async def log_conversation_turn(conn: aiosqlite.Connection, session_id: str, role: str, content: str) -> None:
    await conn.execute(
        "INSERT INTO conversation_turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now()),
    )
    await conn.commit()

async def log_user_turn(conn: aiosqlite.Connection, user_id: str, session_id: str, role: str, content: str, room_name: str = "default") -> None:
    """Ensure user profile and session log exist, then log conversation turn."""
    await get_or_create_profile(conn, user_id)
    await conn.execute(
        "INSERT OR IGNORE INTO session_logs (session_id, user_id, room_name, created_at) VALUES (?, ?, ?, ?)",
        (session_id, user_id, room_name, now()),
    )
    await conn.execute(
        "INSERT INTO conversation_turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now()),
    )
    await conn.commit()

async def get_recent_conversation_turns(conn: aiosqlite.Connection, session_id: str, limit: int = 10) -> List[dict]:
    """Retrieve recent conversation turns for session context."""
    sql = """
        SELECT role, content, timestamp
        FROM conversation_turns
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """
    async with conn.execute(sql, (session_id, limit)) as cur:
        rows = await cur.fetchall()
        # Return in chronological order
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]

