"""External market, macroeconomic, news, and SEC data collectors."""
import asyncio
from datetime import date
import httpx
import pandas as pd
from ..core.config import settings


async def fetch_json(url: str, params: dict | None = None, timeout: float = 10,
                     retries: int = 2, headers: dict | None = None) -> dict:
    last_error = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                await asyncio.sleep(0.2 * (attempt + 1))
    raise RuntimeError(f"Unable to fetch {url}") from last_error


async def fetch_fred_observations(
    api_key: str,
    series_id: str,
    start: date,
    end: date,
) -> list[dict]:
    if not api_key:
        raise ValueError("FRED API key is required")
    payload = await fetch_json(
        "https://api.stlouisfed.org/fred/series/observations",
        {
            "api_key": api_key,
            "series_id": series_id,
            "observation_start": start.isoformat(),
            "observation_end": end.isoformat(),
            "file_type": "json",
        },
    )
    observations = []
    for item in payload.get("observations", []):
        if item.get("value") in (None, "."):
            continue
        observations.append(
            {"date": date.fromisoformat(item["date"]), "value": float(item["value"])}
        )
    return observations


async def fetch_news(
    api_key: str,
    ticker: str,
    start: date,
    end: date,
    page_size: int = 100,
) -> list[dict]:
    if not api_key:
        raise ValueError("NewsAPI key is required")
    payload = await fetch_json(
        settings.news_api_url,
        {
            "q": ticker,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": api_key,
        },
    )
    if payload.get("status") != "ok":
        raise RuntimeError(f"NewsAPI returned an invalid response for {ticker}")
    return [
        {
            "title": item["title"],
            "source": (item.get("source") or {}).get("name"),
            "url": item.get("url"),
            "published_at": item.get("publishedAt"),
            "summary": item.get("description"),
        }
        for item in payload.get("articles", [])
        if item.get("title") and item.get("url")
    ]


async def fetch_sec_filings(user_agent: str, ticker: str, start: date, end: date,
                            limit: int = 20) -> list[dict]:
    """Fetch recent SEC submissions for a ticker without exposing SEC credentials."""
    if not user_agent:
        raise ValueError("SEC_USER_AGENT is required")
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    companies = await fetch_json("https://www.sec.gov/files/company_tickers.json", headers=headers)
    symbol = ticker.upper()
    match = next((item for item in companies.values()
                  if item.get("ticker", "").upper() == symbol), None)
    if not match:
        return []
    cik = str(match["cik_str"]).zfill(10)
    payload = await fetch_json(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers)
    recent = (payload.get("filings") or {}).get("recent") or {}
    results = []
    for index, filing_date in enumerate(recent.get("filingDate", [])):
        filed = date.fromisoformat(filing_date)
        if not start <= filed <= end:
            continue
        accession = recent.get("accessionNumber", [])[index].replace("-", "")
        primary = recent.get("primaryDocument", [])[index]
        results.append({
            "ticker": symbol,
            "form": recent.get("form", [""])[index],
            "filing_date": filing_date,
            "title": f"{recent.get('form', ['Filing'])[index]} filing for {symbol}",
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}",
        })
        if len(results) >= limit:
            break
    return results


def download_prices(ticker: str, start: date, end: date) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed") from exc
    data = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False, timeout=10)
    if data.empty:
        return data
    if hasattr(data.columns, "levels"):
        data.columns = [c[0] if isinstance(c, tuple) else c for c in data.columns]
    data = data.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    required_columns = ["open", "high", "low", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        raise RuntimeError(f"Downloaded price data is missing columns: {missing_columns}")
    return data.loc[:, required_columns]
