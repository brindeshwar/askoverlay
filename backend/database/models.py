from sqlalchemy import Column, String, Integer, Date
from database.connection import Base

class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True)
    request_count = Column(Integer, default=0)
    last_reset_date = Column(Date)