from fastapi import FastAPI
from dotenv import load_dotenv
from database import connection, models  # noqa: F401 — models import required so Base knows about Device before create_all
from routes.chat import router as chat_router

load_dotenv()

connection.Base.metadata.create_all(bind=connection.engine)

app = FastAPI()
app.include_router(chat_router)