import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from config import get_settings
from database import connection, models  # noqa: F401  (models must be imported so Base knows the tables)
from routes.chat import router as chat_router
from routes.health import router as health_router
import redaction

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
redaction.install()  # screenshots must never reach the logs, even inside a library's error message
log = logging.getLogger("askoverlay.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection.Base.metadata.create_all(bind=connection.engine)
    if not settings.backend_gemini_key:
        log.warning("BACKEND_GEMINI_KEY is not set: demo mode will answer 503, BYOK still works")
    log.info(f"AskOverlay backend started (model={settings.gemini_model}, demo limit={settings.demo_request_limit})")
    yield
    connection.engine.dispose()
    log.info("AskOverlay backend stopped")


app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)
app.include_router(health_router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's default 422 echoes each offending input back; for a screenshot that would be hundreds of KB."""
    errors = [
        {key: value for key, value in error.items() if key != "input"} if "screenshot" in error.get("loc", ()) else error
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})
