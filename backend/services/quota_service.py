import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database.models import Device

log = logging.getLogger("askoverlay.quota")

# Lifetime cap per device for the backend-funded demo. No daily reset.
DEMO_REQUEST_LIMIT = 10


def get_demo_usage(db: Session, device_id: str) -> int:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    return device.request_count if device else 0


def check_and_increment_quota(db: Session, device_id: str) -> bool:
    """Consume one demo request for this device. Returns False if the lifetime cap is reached.

    The increment is a single conditional UPDATE, so concurrent requests cannot
    push the counter past the limit (no read-modify-write race).
    """
    if db.query(Device).filter(Device.device_id == device_id).first() is None:
        try:
            db.add(Device(device_id=device_id, request_count=0))
            db.commit()
            log.info("New demo device registered")
        except IntegrityError:
            db.rollback()  # another request registered it first

    updated = (
        db.query(Device)
        .filter(Device.device_id == device_id, Device.request_count < DEMO_REQUEST_LIMIT)
        .update({Device.request_count: Device.request_count + 1}, synchronize_session=False)
    )
    db.commit()

    if updated == 0:
        log.info("Demo quota exhausted for a device")
        return False
    return True
