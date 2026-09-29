"""Backtest record and trade log ORM models."""
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class BacktestRecord(Base):
    __tablename__ = "backtest_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    initial_capital: Mapped[float] = mapped_column(Float)
    final_value: Mapped[float] = mapped_column(Float)
    total_return: Mapped[float] = mapped_column(Float)
    cagr: Mapped[float] = mapped_column(Float)
    mdd: Mapped[float] = mapped_column(Float)
    sharpe_ratio: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="backtests")
    trades = relationship("BacktestTrade", back_populates="backtest", cascade="all, delete-orphan")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtest_records.id"), index=True)
    trade_date: Mapped[date] = mapped_column(Date)
    side: Mapped[str] = mapped_column(String(4))
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float, default=0)
    slippage: Mapped[float] = mapped_column(Float, default=0)
    backtest = relationship("BacktestRecord", back_populates="trades")


class UserAlert(Base):
    __tablename__ = "user_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    condition: Mapped[dict] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    user = relationship("User", back_populates="alerts")
