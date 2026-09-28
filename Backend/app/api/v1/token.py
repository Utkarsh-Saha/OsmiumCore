from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from livekit import api
from app.core.config import settings

router = APIRouter()

class TokenRequest(BaseModel):
    room_name: str = "osmiumcore-default"
    participant_identity: str = "user"

class TokenResponse(BaseModel):
    token: str
    server_url: str

@router.post("/token", response_model=TokenResponse)
async def generate_token(req: TokenRequest):
    try:
        token = api.AccessToken(
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET
        ).with_identity(
            req.participant_identity
        ).with_grants(
            api.VideoGrants(
                room_join=True,
                room=req.room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        
        return TokenResponse(
            token=token.to_jwt(),
            server_url=settings.LIVEKIT_URL
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))