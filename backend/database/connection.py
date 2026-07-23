import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

log = logging.getLogger("askoverlay.database")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./askoverlay.db")
log.info(f"Using database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()