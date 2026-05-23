"""
SmartAC - User Model
Stores user accounts in SQLite on EC2.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, nullable=True, unique=True)
    is_active = Column(Boolean, default=True)
    is_google = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())