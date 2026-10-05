import aiosqlite
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Deterministic default path to osmium_memory.db in the project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = str(PROJECT_ROOT / "osmium_memory.db")

# Path to the SQLite DB file; can be overridden via environment variable
DB_PATH = os.getenv("OSMIUM_MEMORY_DB", DEFAULT_DB_PATH)

@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that provides an open SQLite connection with WAL and FK enabled,
    and guarantees proper closure upon exit.
    """
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.commit()
    try:
        yield conn
    finally:
        await conn.close()

async def init_db() -> None:
    """Create all required tables for the memory subsystem if they don't exist.
    Called on FastAPI startup.
    """
    async with get_connection() as conn:
        # User profiles table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                voice_preference TEXT,
                system_prompt_overrides TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Memories table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                category TEXT,
                content TEXT,
                importance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Full‑text search virtual table for memories
        await conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                content='memories',
                content_rowid='id'
            );
            """
        )
        # Session logs table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_logs (
                session_id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                room_name TEXT,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Conversation turns table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT REFERENCES session_logs(session_id) ON DELETE CASCADE,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await conn.commit()

# FastAPI dependency – yields a connection and guarantees closure.
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with get_connection() as conn:
        yield conn
