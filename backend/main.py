import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from database import connection, models
from routes.chat import router as chat_router
from routes.auth import router as auth_router
from routes.billing import router as billing_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("askoverlay.main")

load_dotenv()

connection.Base.metadata.create_all(bind=connection.engine)

app = FastAPI()
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(billing_router)

log.info("AskOverlay backend started")