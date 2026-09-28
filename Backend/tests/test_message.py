import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, get_connection

@pytest.mark.asyncio
async def test_message_endpoint():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/message",
            json={
                "user_id": "test_user_1",
                "content": "Hello, I am testing the messaging endpoint!",
                "session_id": "test_session_1"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_id"] == "test_user_1"
        assert data["user_message"] == "Hello, I am testing the messaging endpoint!"
        assert "reply" in data
        assert len(data["reply"]) > 0

        # Verify DB user and assistant turns exist
        async with get_connection() as conn:
            async with conn.execute(
                "SELECT role, content FROM conversation_turns WHERE session_id = ? ORDER BY id ASC",
                ("test_session_1",)
            ) as cur:
                rows = await cur.fetchall()
                assert len(rows) >= 2
                roles = [r[0] for r in rows]
                assert "user" in roles
                assert "assistant" in roles
