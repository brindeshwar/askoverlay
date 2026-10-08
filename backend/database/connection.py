import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import get_settings

log = logging.getLogger("askoverlay.database")

DATABASE_URL = get_settings().database_url

# check_same_thread=False: sessions are created in FastAPI's threadpool and may be
# used from a different worker thread than the one that opened them (SQLite only).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
