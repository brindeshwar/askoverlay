from datetime import date
import os
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database.connection import SessionLocal
from database.models import User, Device
from services.gemini_service import stream_gemini_response
from services.quota_service import check_and_increment_quota, check_and_increment_user_quota
from services.auth_service import verify_session_token

router = APIRouter()

BACKEND_GEMINI_KEY = os.getenv("BACKEND_GEMINI_KEY")
TIERED_MODEL = "gemini-2.5-flash-lite"
BYOK_MODEL = "gemini-3.5-flash"

class ChatRequest(BaseModel):
    message: str
    interaction_id: str | None = None

@router.post("/chat")
async def chat(
    request: ChatRequest,
    x_gemini_key: str | None = Header(default=None),
    x_device_id: str | None = Header(default=None),
    x_session_token: str | None = Header(default=None),
):
    if x_gemini_key:
        return StreamingResponse(
            stream_gemini_response(x_gemini_key, BYOK_MODEL, request.message, request.interaction_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    if x_session_token:
        user_id = verify_session_token(x_session_token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid or expired session token.")

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise HTTPException(status_code=404, detail="User not found.")
            allowed = check_and_increment_user_quota(db, user)
        finally:
            db.close()

        if not allowed:
            raise HTTPException(status_code=429, detail="Daily limit reached. Upgrade to Premium for more, or come back tomorrow.")

        return StreamingResponse(
            stream_gemini_response(BACKEND_GEMINI_KEY, TIERED_MODEL, request.message, request.interaction_id),
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
            stream_gemini_response(BACKEND_GEMINI_KEY, TIERED_MODEL, request.message, request.interaction_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    raise HTTPException(status_code=400, detail="Missing X-Gemini-Key or X-Device-Id header.")

@router.get("/quota/status")
def quota_status(
    x_device_id: str | None = Header(default=None),
    x_session_token: str | None = Header(default=None),
):
    if x_session_token:
        user_id = verify_session_token(x_session_token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid session token.")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise HTTPException(status_code=404, detail="User not found.")
            limit = 100 if user.tier == "premium" else 10
            used = user.request_count if user.last_reset_date == date.today() else 0
            return {"mode": user.tier, "used": used, "limit": limit}
        finally:
            db.close()

    if x_device_id:
        db = SessionLocal()
        try:
            device = db.query(Device).filter(Device.device_id == x_device_id).first()
            used = device.request_count if device and device.last_reset_date == date.today() else 0
            return {"mode": "free", "used": used, "limit": 10}
        finally:
            db.close()

    return {"mode": "byok", "used": None, "limit": None}