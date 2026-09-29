"""Backtest condition and result schemas."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Condition(BaseModel):
    indicator: str
    operator: Literal[">", ">=", "<", "<=", "==", "!="]
    value: float

class BacktestRequest(BaseModel):
    ticker: str
    start_date: date
    end_date: date
    initial_capital: float = Field(default=10000, gt=0)
    buy_conditions: list[Condition] = Field(default_factory=list)
    sell_conditions: list[Condition] = Field(default_factory=list)
    commission_rate: float = Field(default=0.0005, ge=0)
    slippage_rate: float = Field(default=0.001, ge=0)
    benchmark_ticker: str | None = Field(default="SPY", min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be later than start_date")
        return self

class TradeResponse(BaseModel):
    trade_date: date
    side: str
    price: float
    quantity: float
    commission: float
    slippage: float

class BacktestResponse(BaseModel):
    ticker: str
    final_value: float
    total_return: float
    cagr: float
    mdd: float
    sharpe_ratio: float
    trade_count: int
    closed_trade_count: int
    trades: list[TradeResponse]
    equity_curve: list[dict]
    benchmark_ticker: str | None = None
    benchmark_return: float | None = None
    excess_return: float | None = None
