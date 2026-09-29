"""User and onboarding profile ORM models."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_profile: Mapped[str | None] = mapped_column(String(30))
    investment_horizon: Mapped[str | None] = mapped_column(String(30))
    widgets: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    backtests = relationship("BacktestRecord", back_populates="user")
    alerts = relationship("UserAlert", back_populates="user", cascade="all, delete-orphan")
