from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.chat_service import generate_chat_reply
from app.core.database import get_connection

router = APIRouter()

class MessagePayload(BaseModel):
    user_id: str = Field(..., description="Unique user identity")
    content: str = Field(..., min_length=1, description="Text message content")
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")

class MessageResponse(BaseModel):
    status: str
    user_id: str
    session_id: str
    user_message: str
    reply: str

@router.post("/message", response_model=MessageResponse, tags=["Messaging"])
async def post_message(payload: MessagePayload):
    """Receive a text message, generate an intelligent assistant reply with memory context,
    persist both turns, and return the reply.
    """
    user_id = payload.user_id.strip()
    content = payload.content.strip()

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if not content:
        raise HTTPException(status_code=400, detail="content cannot be empty")

    session_id = payload.session_id.strip() if payload.session_id and payload.session_id.strip() else f"text-{user_id}"

    async with get_connection() as conn:
        reply = await generate_chat_reply(
            conn=conn,
            user_id=user_id,
            session_id=session_id,
            user_message=content
        )

    return MessageResponse(
        status="success",
        user_id=user_id,
        session_id=session_id,
        user_message=content,
        reply=reply
    )
