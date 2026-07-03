import os
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database.connection import SessionLocal
from services.gemini_service import stream_gemini_response
from services.quota_service import check_and_increment_quota

router = APIRouter()

BACKEND_GEMINI_KEY = os.getenv("BACKEND_GEMINI_KEY")
TIERED_MODEL = "gemini-2.5-flash-lite"
BYOK_MODEL = "gemini-3.5-flash"

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(
    request: ChatRequest,
    x_gemini_key: str | None = Header(default=None),
    x_device_id: str | None = Header(default=None),
):
    if x_gemini_key:
        return StreamingResponse(
            stream_gemini_response(x_gemini_key, BYOK_MODEL, request.message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    if x_device_id:
        db = SessionLocal()
        try:
            allowed = check_and_increment_quota(db, x_device_id)
        finally:
            db.close()

        if not allowed:
            raise HTTPException(status_code=429, detail="Daily free limit reached. Come back tomorrow, or add your own Gemini API key for unlimited use.")

        return StreamingResponse(
            stream_gemini_response(BACKEND_GEMINI_KEY, TIERED_MODEL, request.message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    raise HTTPException(status_code=400, detail="Missing X-Gemini-Key or X-Device-Id header.")