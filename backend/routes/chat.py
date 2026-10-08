# backend/routes/chat
import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from config import Settings, get_settings
from database.connection import get_db
from services.gemini_service import GeminiError, start_stream
from services.quota_service import consume_demo_request, get_demo_usage

log = logging.getLogger("askoverlay.chat")

router = APIRouter()

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

MAX_MESSAGE_CHARS = 8000
# Headers are untrusted input; bounding them keeps garbage out of the database.
DeviceIdHeader = Header(default=None, min_length=8, max_length=64)


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    interaction_id: str | None = Field(default=None, max_length=256)


async def _stream(api_key: str, request: ChatRequest, settings: Settings) -> StreamingResponse:
    try:
        lines = await start_stream(
            api_key,
            settings.gemini_model,
            request.message,
            request.interaction_id,
            settings.gemini_timeout_seconds,
        )
    except GeminiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return StreamingResponse(lines, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    x_gemini_key: str | None = Header(default=None),
    x_device_id: str | None = DeviceIdHeader,
    settings: Settings = Depends(get_settings),
):
    if x_gemini_key:
        log.info("Routing: BYOK path")
        return await _stream(x_gemini_key, request, settings)

    if x_device_id:
        log.info("Routing: demo (device) path")
        if not settings.backend_gemini_key:
            log.error("Demo requested but BACKEND_GEMINI_KEY is not configured")
            raise HTTPException(status_code=503, detail="The demo is not available right now. Add your own Gemini API key to use AskOverlay.")

        # Blocking DB work runs in the threadpool so it can't stall other users' streams.
        allowed = await run_in_threadpool(consume_demo_request, x_device_id, settings.demo_request_limit)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Demo limit reached ({settings.demo_request_limit} requests). Add your own Gemini API key to keep using AskOverlay.",
            )
        return await _stream(settings.backend_gemini_key, request, settings)

    log.warning("Chat request with no valid auth header")
    raise HTTPException(status_code=400, detail="Missing X-Gemini-Key or X-Device-Id header.")


@router.get("/quota/status")
def quota_status(
    x_device_id: str | None = DeviceIdHeader,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if x_device_id:
        return {"mode": "demo", "used": get_demo_usage(db, x_device_id), "limit": settings.demo_request_limit}

    return {"mode": "byok", "used": None, "limit": None}
