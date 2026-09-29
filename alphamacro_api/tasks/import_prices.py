"""Download OHLCV data and persist technical indicators."""
from __future__ import annotations

import argparse
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import Base, SessionLocal, engine
from ..models import StockPrice
from ..services.collector import download_prices
from ..services.macro_analytics import macd, rsi


def _as_date(value: object) -> date:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.date()


def import_prices(ticker: str, start: date, end: date, db: Session) -> int:
    """Download and upsert prices for one ticker. Returns the row count."""
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker must not be empty")
    if end <= start:
        raise ValueError("end must be later than start")

    frame = download_prices(normalized_ticker, start, end)
    if frame.empty:
        raise RuntimeError(f"No price data returned for {normalized_ticker}")

    frame = frame.sort_index()
    close = pd.to_numeric(frame["close"], errors="coerce")
    rsi_values = rsi(close)
    macd_values, signal_values = macd(close)
    saved = 0

    for timestamp, row in frame.iterrows():
        values = {
            "open_price": float(row["open"]),
            "high_price": float(row["high"]),
            "low_price": float(row["low"]),
            "close_price": float(row["close"]),
            "volume": int(row["volume"]) if pd.notna(row["volume"]) else 0,
            "rsi_14": float(rsi_values.loc[timestamp]) if pd.notna(rsi_values.loc[timestamp]) else None,
            "macd": float(macd_values.loc[timestamp]) if pd.notna(macd_values.loc[timestamp]) else None,
            "macd_signal": float(signal_values.loc[timestamp]) if pd.notna(signal_values.loc[timestamp]) else None,
        }
        if any(pd.isna(values[key]) for key in ("open_price", "high_price", "low_price", "close_price")):
            continue

        price_date = _as_date(timestamp)
        existing = db.scalar(
            select(StockPrice).where(
                StockPrice.ticker == normalized_ticker,
                StockPrice.date == price_date,
            )
        )
        if existing is None:
            db.add(StockPrice(ticker=normalized_ticker, date=price_date, **values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        saved += 1

    db.commit()
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Import yfinance prices into AlphaMacro")
    parser.add_argument("ticker")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = import_prices(args.ticker, args.start, args.end, db)
    print(f"Imported {count} rows for {args.ticker.upper()}")


if __name__ == "__main__":
    main()
