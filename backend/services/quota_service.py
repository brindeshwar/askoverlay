from datetime import date
from sqlalchemy.orm import Session
from database.models import Device

FREE_TIER_LIMIT = 10
PREMIUM_TIER_LIMIT = 100

def check_and_increment_user_quota(db: Session, user) -> bool:
    today = date.today()
    limit = PREMIUM_TIER_LIMIT if user.tier == "premium" else FREE_TIER_LIMIT

    if user.last_reset_date != today:
        user.request_count = 0
        user.last_reset_date = today

    if user.request_count >= limit:
        db.commit()
        return False

    user.request_count += 1
    db.commit()
    return True

def check_and_increment_quota(db: Session, device_id: str) -> bool:
    today = date.today()
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if device is None:
        device = Device(device_id=device_id, request_count=0, last_reset_date=today)
        db.add(device)

    if device.last_reset_date != today:
        device.request_count = 0
        device.last_reset_date = today

    if device.request_count >= FREE_TIER_LIMIT:
        db.commit()
        return False

    device.request_count += 1
    db.commit()
    return True