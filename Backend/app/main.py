from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from Backend.app.api.v1 import token

app = FastAPI(title="OsmiumCore Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(token.router, prefix="/api/v1", tags=["Authentication"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "osmiumcore-backend"}