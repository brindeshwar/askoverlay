from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from database.connection import SessionLocal
from services.auth_service import verify_session_token
from database.models import User
from services.paypal_service import create_order, capture_order

router = APIRouter()

BACKEND_PUBLIC_URL = "http://localhost:8000"  # becomes your EC2 URL after deployment


@router.post("/billing/checkout")
def create_checkout(x_session_token: str = Header(...)):
    user_id = verify_session_token(x_session_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token. Please log in again.")

    result = create_order(
        custom_id=str(user_id),
        return_url=f"{BACKEND_PUBLIC_URL}/billing/success",
        cancel_url=f"{BACKEND_PUBLIC_URL}/billing/cancel",
    )
    return {"approve_url": result["approve_url"]}


@router.get("/billing/success", response_class=HTMLResponse)
def billing_success(token: str):
    db = SessionLocal()
    try:
        capture_result = capture_order(token)
        custom_id = capture_result["purchase_units"][0]["payments"]["captures"][0]["custom_id"]
        user = db.query(User).filter(User.id == int(custom_id)).first()
        if user:
            user.tier = "premium"
            db.commit()
    finally:
        db.close()

    return "<html><body><h2>Payment successful! You're now on Premium. You can close this window and return to AskOverlay.</h2></body></html>"


@router.get("/billing/cancel", response_class=HTMLResponse)
def billing_cancel():
    return "<html><body><h2>Payment cancelled. You can close this window.</h2></body></html>"