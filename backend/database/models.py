from sqlalchemy import Column, String, Integer
from database.connection import Base

class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True)
    request_count = Column(Integer, default=0, nullable=False)
