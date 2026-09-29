"""Macro correlation analysis schemas."""
from typing import Literal
from pydantic import BaseModel, Field

class CorrelationQuery(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    indicator: str
    period: str = "1Y"
    correlation_type: Literal["return", "price"] = "return"

class CorrelationResponse(BaseModel):
    ticker: str
    indicator: str
    correlation: float | None
    correlation_type: str
    latest_rsi: float | None = None
    latest_macd: float | None = None
    dates: list[str] = Field(default_factory=list)
    stock_returns: list[float] = Field(default_factory=list)
    indicator_returns: list[float] = Field(default_factory=list)
