# backend/routes/chat
import logging
import os
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.connection import get_db
from services.gemini_service import stream_gemini_response
from services.quota_service import DEMO_REQUEST_LIMIT, check_and_increment_quota, get_demo_usage

log = logging.getLogger("askoverlay.chat")

router = APIRouter()

BACKEND_GEMINI_KEY = os.getenv("BACKEND_GEMINI_KEY")
MODEL = "gemini-3.5-flash-lite"

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class ChatRequest(BaseModel):
    message: str
    interaction_id: str | None = None


def _stream(api_key: str, request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_gemini_response(api_key, MODEL, request.message, request.interaction_id),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    x_gemini_key: str | None = Header(default=None),
    x_device_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if x_gemini_key:
        log.info("Routing: BYOK path")
        return _stream(x_gemini_key, request)

    if x_device_id:
        log.info("Routing: demo (device) path")
        if not check_and_increment_quota(db, x_device_id):
            raise HTTPException(
                status_code=429,
                detail=f"Demo limit reached ({DEMO_REQUEST_LIMIT} requests). Add your own Gemini API key to keep using AskOverlay.",
            )
        return _stream(BACKEND_GEMINI_KEY, request)

    log.warning("Chat request with no valid auth header")
    raise HTTPException(status_code=400, detail="Missing X-Gemini-Key or X-Device-Id header.")


@router.get("/quota/status")
def quota_status(
    x_device_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if x_device_id:
        return {"mode": "demo", "used": get_demo_usage(db, x_device_id), "limit": DEMO_REQUEST_LIMIT}

    return {"mode": "byok", "used": None, "limit": None}
