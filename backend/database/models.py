from sqlalchemy import Column, String, Integer, Date
from database.connection import Base

class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True)
    request_count = Column(Integer, default=0)
    last_reset_date = Column(Date)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String)
    name = Column(String)
    refresh_token = Column(String)
    tier = Column(String, default="free")
    request_count = Column(Integer, default=0)
    last_reset_date = Column(Date)