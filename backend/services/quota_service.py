import logging
from datetime import date
from sqlalchemy.orm import Session
from database.models import Device

log = logging.getLogger("askoverlay.quota")

FREE_TIER_LIMIT = 10
PREMIUM_TIER_LIMIT = 100

def check_and_increment_user_quota(db: Session, user) -> bool:
    today = date.today()
    limit = PREMIUM_TIER_LIMIT if user.tier == "premium" else FREE_TIER_LIMIT

    if user.last_reset_date != today:
        log.info(f"Resetting daily count for user_id={user.id}")
        user.request_count = 0
        user.last_reset_date = today

    if user.request_count >= limit:
        log.info(f"Quota exceeded: user_id={user.id}, tier={user.tier}, count={user.request_count}/{limit}")
        db.commit()
        return False

    user.request_count += 1
    db.commit()
    log.info(f"Quota check passed: user_id={user.id}, tier={user.tier}, count={user.request_count}/{limit}")
    return True

def check_and_increment_quota(db: Session, device_id: str) -> bool:
    today = date.today()
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if device is None:
        log.info(f"New device registered: {device_id}")
        device = Device(device_id=device_id, request_count=0, last_reset_date=today)
        db.add(device)

    if device.last_reset_date != today:
        log.info(f"Resetting daily count for device={device_id}")
        device.request_count = 0
        device.last_reset_date = today

    if device.request_count >= FREE_TIER_LIMIT:
        log.info(f"Quota exceeded: device={device_id}, count={device.request_count}/{FREE_TIER_LIMIT}")
        db.commit()
        return False

    device.request_count += 1
    db.commit()
    log.info(f"Quota check passed: device={device_id}, count={device.request_count}/{FREE_TIER_LIMIT}")
    return True