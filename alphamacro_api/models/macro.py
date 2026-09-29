"""Macro indicator ORM models."""
from datetime import date
from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"
    __table_args__ = (UniqueConstraint("indicator", "date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    indicator: Mapped[str] = mapped_column(String(50), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(100))
