import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config import get_settings
from database import connection, models  # noqa: F401  (models must be imported so Base knows the tables)
from routes.chat import router as chat_router
from routes.health import router as health_router

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
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
