import os
import jwt
import logging
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from database.models import User

log = logging.getLogger("askoverlay.auth")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
SESSION_TOKEN_EXPIRY_DAYS = 30

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def build_google_login_url(redirect_uri: str) -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    log.info(f"Building login URL for redirect_uri={redirect_uri}")
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    log.info("Exchanging authorization code for tokens")
    response = requests.post(GOOGLE_TOKEN_URL, data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    response.raise_for_status()
    log.info("Token exchange successful")
    return response.json()


def fetch_google_profile(access_token: str) -> dict:
    response = requests.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    response.raise_for_status()
    profile = response.json()
    log.info(f"Fetched profile for email={profile.get('email')}")
    return profile


def upsert_user(db: Session, profile: dict, refresh_token: str | None) -> User:
    google_id = profile["sub"]
    user = db.query(User).filter(User.google_id == google_id).first()

    if user is None:
        log.info(f"Creating new user: google_id={google_id}, email={profile.get('email')}")
        user = User(
            google_id=google_id,
            email=profile.get("email"),
            name=profile.get("name"),
            refresh_token=refresh_token,
            tier="free",
            request_count=0,
        )
        db.add(user)
    else:
        log.info(f"Updating existing user: id={user.id}, email={profile.get('email')}")
        user.email = profile.get("email")
        user.name = profile.get("name")
        if refresh_token:
            user.refresh_token = refresh_token

    db.commit()
    db.refresh(user)
    return user


def create_session_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_TOKEN_EXPIRY_DAYS),
    }
    log.info(f"Creating session token for user_id={user_id}")
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_session_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except jwt.PyJWTError as e:
        log.warning(f"Session token verification failed: {e}")
        return None