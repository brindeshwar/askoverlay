import enum
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import DailyUsage, Device

log = logging.getLogger("askoverlay.quota")


@dataclass(frozen=True)
class DemoLimits:
    device_lifetime: int  # requests one device may ever make
    ip_daily: int         # requests one client IP may make per UTC day
    global_daily: int     # requests the whole demo may serve per UTC day


class DemoDecision(enum.Enum):
    ALLOWED = "allowed"
    DEVICE_LIMIT = "device_limit"
    IP_LIMIT = "ip_limit"
    GLOBAL_LIMIT = "global_limit"


def _today() -> date:
    return datetime.now(timezone.utc).date()


def get_demo_usage(db: Session, device_id: str) -> int:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    return device.request_count if device else 0


# Each _bump_* is ONE statement: insert the row with count=1, or on conflict add 1 only
# while the count is below the limit. rowcount is 1 if the request was counted and 0 if
# the cap was already reached, so concurrent requests can never push a counter past its
# limit (no read-modify-write race).

def _bump_device(db: Session, device_id: str, limit: int) -> bool:
    stmt = insert(Device).values(device_id=device_id, request_count=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Device.device_id],
        set_={"request_count": Device.request_count + 1},
        where=Device.request_count < limit,
    )
    return db.execute(stmt).rowcount == 1


def _bump_daily(db: Session, day: date, scope: str, key: str, limit: int) -> bool:
    stmt = insert(DailyUsage).values(day=day, scope=scope, key=key, request_count=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[DailyUsage.day, DailyUsage.scope, DailyUsage.key],
        set_={"request_count": DailyUsage.request_count + 1},
        where=DailyUsage.request_count < limit,
    )
    return db.execute(stmt).rowcount == 1


def consume_demo_request(device_id: str, ip: str, limits: DemoLimits) -> DemoDecision:
    """Try to spend one demo request against the device, IP and global caps, all or nothing.

    All three counters are bumped in one transaction; the first cap that is already
    reached rolls the whole thing back, so a rejected request consumes nothing anywhere.
    The device cap is checked first so a user who simply used up their 10 sees the
    actionable message rather than a generic capacity one.

    Runs in its own short-lived session: /chat streams for seconds, and holding a
    request-scoped session open for that long would pin a connection for no reason.
    """
    today = _today()
    checks = (
        (DemoDecision.DEVICE_LIMIT, lambda db: _bump_device(db, device_id, limits.device_lifetime)),
        (DemoDecision.IP_LIMIT, lambda db: _bump_daily(db, today, "ip", ip, limits.ip_daily)),
        (DemoDecision.GLOBAL_LIMIT, lambda db: _bump_daily(db, today, "global", "", limits.global_daily)),
    )
    with SessionLocal() as db:
        for decision, bump in checks:
            if not bump(db):
                db.rollback()
                log.info(f"Demo request rejected: {decision.value}")
                return decision
        db.commit()
    return DemoDecision.ALLOWED


def refund_demo_request(device_id: str, ip: str) -> None:
    """Give back a demo request that failed before Gemini produced anything (our fault, not the user's)."""
    today = _today()
    with SessionLocal() as db:
        db.execute(
            update(Device).where(Device.device_id == device_id, Device.request_count > 0)
            .values(request_count=Device.request_count - 1)
        )
        for scope, key in (("ip", ip), ("global", "")):
            db.execute(
                update(DailyUsage)
                .where(DailyUsage.day == today, DailyUsage.scope == scope, DailyUsage.key == key, DailyUsage.request_count > 0)
                .values(request_count=DailyUsage.request_count - 1)
            )
        db.commit()
    log.info("Refunded a demo request after an upstream failure")
