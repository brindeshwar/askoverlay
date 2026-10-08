# backend/routes/chat
import logging
from fastapi import APIRouter, Header, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from config import Settings, get_settings
from database.connection import get_db
from agent.errors import ChatError
from services.chat_service import start_chat_stream
from services.quota_service import DemoDecision, DemoLimits, consume_demo_request, get_demo_usage, refund_demo_request

log = logging.getLogger("askoverlay.chat")

router = APIRouter()

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

MAX_MESSAGE_CHARS = 8000
MAX_HISTORY_TURNS = 40
MAX_REQUEST_CHARS = 60_000  # message + history together; bounds the tokens one request can spend
# Headers are untrusted input; bounding them keeps garbage out of the database.
DeviceIdHeader = Header(default=None, min_length=8, max_length=64)


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    # Past assistant replies can be long, so a turn is bounded only by the whole-request budget below.
    content: str = Field(max_length=MAX_REQUEST_CHARS)


class ChatRequest(BaseModel):
    """The server keeps no conversation state: the client sends the turns so far with every request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)

    @model_validator(mode="after")
    def bounded_total_size(self):
        total = len(self.message) + sum(len(turn.content) for turn in self.history)
        if total > MAX_REQUEST_CHARS:
            raise ValueError(f"conversation too large ({total} characters, limit {MAX_REQUEST_CHARS})")
        return self


def client_ip(request: Request, settings: Settings) -> str:
    """The caller's IP, used for the per-IP demo cap.

    X-Forwarded-For is client-controlled unless a proxy we run appends to it, so it is
    only believed when trust_forwarded_for is set - and then only its LAST entry, the
    one our own proxy added.
    """
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


async def _stream(api_key: str, request: ChatRequest, settings: Settings) -> StreamingResponse:
    history = [(turn.role, turn.content) for turn in request.history]
    try:
        lines = await start_chat_stream(api_key, history, request.message, settings)
    except ChatError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return StreamingResponse(lines, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    http_request: Request,
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
            raise HTTPException(
                status_code=503,
                detail="The demo is not available right now. Add your own Gemini API key to use AskOverlay.",
            )

        ip = client_ip(http_request, settings)
        limits = DemoLimits(settings.demo_request_limit, settings.demo_ip_daily_limit, settings.demo_global_daily_limit)

        # Blocking DB work runs in the threadpool so it can't stall other users' streams.
        decision = await run_in_threadpool(consume_demo_request, x_device_id, ip, limits)
        if decision is DemoDecision.DEVICE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Demo limit reached ({settings.demo_request_limit} requests). "
                    "Add your own Gemini API key to keep using AskOverlay."
                ),
            )
        if decision is DemoDecision.IP_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many demo requests from your network today. Try again tomorrow, or add your own Gemini API key.",
            )
        if decision is DemoDecision.GLOBAL_LIMIT:
            raise HTTPException(
                status_code=503,
                detail="The demo has reached its daily capacity. Come back tomorrow, or add your own Gemini API key.",
            )

        try:
            return await _stream(settings.backend_gemini_key, request, settings)
        except HTTPException:
            # Gemini failed before answering: that is our problem, not the user's, so don't charge them for it.
            await run_in_threadpool(refund_demo_request, x_device_id, ip)
            raise

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
