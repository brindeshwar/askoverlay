from sqlalchemy import Column, Date, Integer, String
from database.connection import Base


class Device(Base):
    """Lifetime demo usage for one client-generated device id."""

    __tablename__ = "devices"

    device_id = Column(String, primary_key=True)
    request_count = Column(Integer, default=0, nullable=False)


class DailyUsage(Base):
    """Demo usage per UTC day, either per client IP (scope "ip") or for the whole service (scope "global").

    Device ids are forgeable, so these two counters are the real abuse boundary.
    """

    __tablename__ = "daily_usage"

    day = Column(Date, primary_key=True)
    scope = Column(String, primary_key=True)
    key = Column(String, primary_key=True)  # client ip, or "" for the global row
    request_count = Column(Integer, default=0, nullable=False)
