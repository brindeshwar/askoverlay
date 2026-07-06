from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.connection import SessionLocal
from services.auth_service import (
    build_google_login_url,
    exchange_code_for_tokens,
    fetch_google_profile,
    upsert_user,
    create_session_token,
)

router = APIRouter()


@router.get("/auth/google/login")
def google_login(redirect_uri: str):
    return {"login_url": build_google_login_url(redirect_uri)}


class GoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


@router.post("/auth/google/callback")
def google_callback(request: GoogleCallbackRequest):
    try:
        tokens = exchange_code_for_tokens(request.code, request.redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    try:
        profile = fetch_google_profile(access_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch profile: {str(e)}")

    db = SessionLocal()
    try:
        user = upsert_user(db, profile, refresh_token)
        session_token = create_session_token(user.id)
    finally:
        db.close()

    return {"session_token": session_token, "email": user.email, "name": user.name}
