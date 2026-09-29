"""Macro correlation endpoints under /api/v1/macro."""
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import MacroIndicator, StockPrice
from ..schemas.macro import CorrelationResponse
from ..services.macro_analytics import correlation, rsi, macd
router = APIRouter()

@router.get("/correlation", response_model=CorrelationResponse)
def get_correlation(ticker: str, indicator: str, period: str = "1Y", correlation_type: str = "return",
                    db: Session = Depends(get_db)):
    normalized_period = period.upper()
    period_days = {"1M": 31, "3M": 93, "1Y": 365, "5Y": 1825}
    days = period_days.get(normalized_period)
    if days is None:
        raise HTTPException(422, "period must be one of 1M, 3M, 1Y, or 5Y")
    stocks = db.scalars(select(StockPrice).where(StockPrice.ticker == ticker).order_by(StockPrice.date)).all()
    macros = db.scalars(select(MacroIndicator).where(MacroIndicator.indicator == indicator).order_by(MacroIndicator.date)).all()
    if not stocks or not macros:
        raise HTTPException(404, "Market data not found")
    sdf = pd.Series({x.date: x.close_price for x in stocks[-days:]})
    mdf = pd.Series({x.date: x.value for x in macros[-days:]})
    result = correlation(sdf, mdf, correlation_type == "return")
    close = pd.Series(sdf)
    line, signal = macd(close)
    return CorrelationResponse(ticker=ticker, indicator=indicator, correlation=result["value"],
                               correlation_type=correlation_type, latest_rsi=float(rsi(close).iloc[-1]) if len(close) > 14 else None,
                               latest_macd=float(line.iloc[-1]), dates=result["dates"], stock_returns=result["stock"],
                               indicator_returns=result["indicator"])
