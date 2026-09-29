"""Backtesting endpoints under /api/v1/backtest."""
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import BacktestRecord, BacktestTrade, MacroIndicator, StockPrice
from ..schemas.backtest import BacktestRequest, BacktestResponse
from ..core.security import get_current_user
from ..services.backtest_engine import buy_and_hold, run_backtest
router = APIRouter()

@router.post("/run", response_model=BacktestResponse)
def run(payload: BacktestRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    prices = db.scalars(select(StockPrice).where(StockPrice.ticker == payload.ticker.upper(),
        StockPrice.date >= payload.start_date, StockPrice.date <= payload.end_date).order_by(StockPrice.date)).all()
    if len(prices) < 2:
        raise HTTPException(404, "At least two price rows are required")
    frame = pd.DataFrame([{
        "open": x.open_price,
        "close": x.close_price,
        "RSI": x.rsi_14,
        "MACD": x.macd,
        "MACD_SIGNAL": x.macd_signal,
        "date": x.date,
    } for x in prices]).set_index("date")
    indicators = {condition.indicator for condition in (*payload.buy_conditions, *payload.sell_conditions)}
    indicators -= {"RSI", "MACD", "MACD_SIGNAL"}
    if indicators:
        macro_rows = db.scalars(select(MacroIndicator).where(
            MacroIndicator.indicator.in_(indicators),
            MacroIndicator.date >= payload.start_date,
            MacroIndicator.date <= payload.end_date,
        )).all()
        for indicator in indicators:
            values = {row.date: row.value for row in macro_rows if row.indicator == indicator}
            frame[indicator] = pd.Series(values)
    frame = frame.dropna(subset=["open", "close"])
    result = run_backtest(frame, payload.initial_capital, [x.model_dump() for x in payload.buy_conditions],
                          [x.model_dump() for x in payload.sell_conditions], payload.commission_rate, payload.slippage_rate)
    benchmark_return = None
    benchmark_ticker = payload.benchmark_ticker.upper() if payload.benchmark_ticker else None
    if benchmark_ticker:
        benchmark_prices = db.scalars(select(StockPrice).where(
            StockPrice.ticker == benchmark_ticker,
            StockPrice.date >= payload.start_date,
            StockPrice.date <= payload.end_date,
        ).order_by(StockPrice.date)).all()
        if len(benchmark_prices) >= 2:
            benchmark_frame = pd.DataFrame([{
                "open": x.open_price, "close": x.close_price, "date": x.date
            } for x in benchmark_prices]).set_index("date")
            benchmark_return = buy_and_hold(benchmark_frame, payload.initial_capital)["total_return"]
    record = BacktestRecord(
        user_id=user.id,
        ticker=payload.ticker.upper(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=payload.initial_capital,
        final_value=result["final_value"],
        total_return=result["total_return"],
        cagr=result["cagr"],
        mdd=result["mdd"],
        sharpe_ratio=result["sharpe_ratio"],
    )
    record.trades = [BacktestTrade(**trade) for trade in result["trades"]]
    db.add(record)
    db.commit()
    result.update({
        "benchmark_ticker": benchmark_ticker,
        "benchmark_return": benchmark_return,
        "excess_return": result["total_return"] - benchmark_return if benchmark_return is not None else None,
    })
    return BacktestResponse(ticker=payload.ticker.upper(), **result)


@router.get("/history", response_model=list[BacktestResponse])
def history(db: Session = Depends(get_db), user=Depends(get_current_user)):
    records = db.scalars(
        select(BacktestRecord).where(BacktestRecord.user_id == user.id)
        .order_by(BacktestRecord.created_at.desc())
    ).all()
    return [
        BacktestResponse(
            ticker=record.ticker,
            final_value=record.final_value,
            total_return=record.total_return,
            cagr=record.cagr,
            mdd=record.mdd,
            sharpe_ratio=record.sharpe_ratio,
            trade_count=len(record.trades),
            closed_trade_count=sum(trade.side == "SELL" for trade in record.trades),
            trades=[{
                "trade_date": trade.trade_date,
                "side": trade.side,
                "price": trade.price,
                "quantity": trade.quantity,
                "commission": trade.commission,
                "slippage": trade.slippage,
            } for trade in record.trades],
            equity_curve=[],
        )
        for record in records
    ]
