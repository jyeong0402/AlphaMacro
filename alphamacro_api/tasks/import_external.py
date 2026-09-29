"""Import FRED indicators and NewsAPI articles into the local database."""
from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import Base, SessionLocal, engine
from ..models import FinancialNews, MacroIndicator
from ..services.collector import fetch_fred_observations, fetch_news


def save_fred(
    db: Session,
    indicator: str,
    observations: list[dict],
) -> int:
    saved = 0
    for observation in observations:
        existing = db.scalar(
            select(MacroIndicator).where(
                MacroIndicator.indicator == indicator,
                MacroIndicator.date == observation["date"],
            )
        )
        if existing is None:
            db.add(
                MacroIndicator(
                    indicator=indicator,
                    date=observation["date"],
                    value=observation["value"],
                    source="FRED",
                )
            )
        else:
            existing.value = observation["value"]
            existing.source = "FRED"
        saved += 1
    return saved


def save_news(db: Session, ticker: str, articles: list[dict]) -> int:
    saved = 0
    for article in articles:
        url = article["url"]
        existing = db.scalar(
            select(FinancialNews).where(
                FinancialNews.ticker == ticker,
                FinancialNews.url == url,
            )
        )
        published_at = (
            datetime.fromisoformat(article["published_at"].replace("Z", "+00:00")).replace(
                tzinfo=None
            )
            if article.get("published_at")
            else None
        )
        values = {key: value for key, value in article.items() if key != "published_at"}
        if existing is None:
            db.add(FinancialNews(ticker=ticker, **values, published_at=published_at))
        else:
            existing.title = article["title"]
            existing.summary = article["summary"]
            existing.source = article["source"]
            existing.published_at = published_at
        saved += 1
    return saved


async def import_external(
    indicator: str,
    series_id: str,
    ticker: str,
    start: date,
    end: date,
) -> tuple[int, int]:
    fred = await fetch_fred_observations(settings.fred_api_key or "", series_id, start, end)
    news = await fetch_news(settings.news_api_key or "", ticker, start, end) if ticker else []
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        fred_count = save_fred(db, indicator, fred)
        news_count = save_news(db, ticker.upper(), news) if ticker else 0
        db.commit()
    return fred_count, news_count


async def import_news(ticker: str, start: date, end: date) -> int:
    """Fetch and persist NewsAPI articles for one ticker."""
    articles = await fetch_news(settings.news_api_key or "", ticker, start, end)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = save_news(db, ticker.upper(), articles)
        db.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import FRED and NewsAPI data")
    parser.add_argument("--indicator", required=True, help="Local indicator name, e.g. DFF")
    parser.add_argument("--series-id", required=True, help="FRED series ID, e.g. DFF")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    fred_count, news_count = asyncio.run(
        import_external(
            args.indicator,
            args.series_id,
            args.ticker,
            args.start,
            args.end,
        )
    )
    print(f"Imported FRED rows: {fred_count}; NewsAPI rows: {news_count}")


if __name__ == "__main__":
    main()
