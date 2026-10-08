import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_db

log = logging.getLogger("askoverlay.health")

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Liveness plus a database round-trip; used by the container healthcheck."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        log.error("Health check failed: database unreachable", exc_info=True)
        raise HTTPException(status_code=503, detail="database unavailable") from None
    return {"status": "ok"}
