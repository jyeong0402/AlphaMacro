"""DST-aware scheduled refresh of configured market and external data."""
from datetime import date, datetime, time, timedelta
import asyncio
import logging
from zoneinfo import ZoneInfo
from ..core.config import settings
from .import_external import import_external, import_news
from .import_prices import import_prices
from ..database import Base, SessionLocal, engine

logger = logging.getLogger(__name__)

def refresh_due(now: datetime | None = None) -> bool:
    local = (now or datetime.now(ZoneInfo("Asia/Seoul"))).astimezone(ZoneInfo("Asia/Seoul"))
    return local.time() >= time(6, 0)

def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


async def refresh_all(now: datetime | None = None) -> dict:
    """Refresh configured tickers and FRED series, returning per-source results."""
    checked_at = (now or datetime.now(ZoneInfo("Asia/Seoul"))).isoformat()
    if not settings.refresh_enabled:
        return {"status": "disabled", "checked_at": checked_at, "results": []}

    end = date.today()
    start = end - timedelta(days=max(settings.refresh_lookback_days, 1))
    results: list[dict] = []
    Base.metadata.create_all(bind=engine)

    for ticker in _csv_values(settings.refresh_tickers):
        try:
            with SessionLocal() as db:
                count = await asyncio.to_thread(import_prices, ticker, start, end, db)
            results.append({"source": "yfinance", "ticker": ticker.upper(), "rows": count, "status": "ok"})
        except Exception as exc:
            logger.exception("yfinance refresh failed for %s", ticker)
            results.append({"source": "yfinance", "ticker": ticker.upper(), "status": "error", "error": str(exc)})
        if settings.news_api_key:
            try:
                count = await import_news(ticker, start, end)
                results.append({"source": "newsapi", "ticker": ticker.upper(), "rows": count, "status": "ok"})
            except Exception as exc:
                logger.exception("NewsAPI refresh failed for %s", ticker)
                results.append({"source": "newsapi", "ticker": ticker.upper(), "status": "error", "error": str(exc)})

    for item in _csv_values(settings.refresh_fred_series):
        if ":" in item:
            indicator, series_id = item.split(":", 1)
        else:
            indicator = series_id = item
        try:
            fred_count, _ = await import_external(indicator, series_id, "", start, end)
            results.append({"source": "fred", "indicator": indicator, "rows": fred_count, "status": "ok"})
        except Exception as exc:
            logger.exception("FRED refresh failed for %s", series_id)
            results.append({"source": "fred", "indicator": indicator, "status": "error", "error": str(exc)})

    return {"status": "ok" if all(item["status"] == "ok" for item in results) else "degraded",
            "checked_at": checked_at, "results": results}


async def refresh_loop(stop_event: asyncio.Event) -> None:
    """Run an initial refresh and then repeat at the configured interval."""
    interval = max(settings.refresh_interval_hours, 1) * 3600
    while not stop_event.is_set():
        await refresh_all()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
