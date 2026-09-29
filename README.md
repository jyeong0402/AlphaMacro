# AlphaMacro API

Runnable FastAPI MVP for macro/stock analytics, sentiment scoring, and backtesting.

```powershell
pip install -r alphamacro_api\requirements.txt
uvicorn alphamacro_api.main:app --reload
```

## Frontend dashboard

With the API running, serve the static dashboard:

```powershell
cd frontend
python -m http.server 8080
```

Open <http://localhost:8080>. The dashboard reads macro correlation, sentiment,
recent news, and submits authenticated backtests. Provider keys remain server-side
in `.env`.

Copy `.env.example` to `.env`, then set `FRED_API_KEY`, `NEWS_API_KEY`, and a
descriptive `SEC_USER_AGENT` (SEC requires an identifying User-Agent).
Never commit `.env` or expose either key in frontend code.

## Scheduled data refresh

Set `REFRESH_ENABLED=true` to run the built-in refresh loop. Configure
`REFRESH_TICKERS=SPY,NVDA` and `REFRESH_FRED_SERIES=DFF:DFF,DGS10:DGS10`.
The loop stores recent yfinance prices, FRED observations, and NewsAPI articles,
then repeats every `REFRESH_INTERVAL_HOURS`.

## PostgreSQL and Redis

Start the operational dependencies with `docker compose up -d`, then set:

```dotenv
DATABASE_URL=postgresql+psycopg2://alphamacro:alphamacro@localhost:5432/alphamacro
REDIS_URL=redis://localhost:6379/0
```

For local SQLite development, keep `DATABASE_URL=sqlite:///./alphamacro.db`.

## Verification status

The repository contains the application and Docker Compose configuration, but
this environment does not provide an installed Python/Node runtime or Docker
daemon. Therefore the API server, frontend server, integration tests, and
containers have not been executed here. On a machine with the dependencies
installed, run:

```powershell
pip install -r alphamacro_api\requirements.txt
uvicorn alphamacro_api.main:app --reload
```

In a second terminal, start PostgreSQL and Redis with `docker compose up -d`,
then serve the dashboard from `frontend` with `python -m http.server 8080`.

## Alerts and real-time updates

Authenticated alerts are available at `GET/POST /api/v1/alerts`; use
`PATCH` or `DELETE /api/v1/alerts/{id}` to manage an alert. Connect to
`/api/v1/alerts/ws?token=<access-token>` to receive JSON alert events.
Redis pub/sub is used when available, with a process-local fallback for development.

Alert conditions use the following shape and are checked against the latest
stored data every `ALERT_CHECK_INTERVAL_SECONDS` (default: 60):

```json
{
  "ticker": "NVDA",
  "indicator": "RSI",
  "operator": "<=",
  "value": 30
}
```

Supported stock indicators are `PRICE`, `CLOSE`, `RSI`, `MACD`, and
`MACD_SIGNAL`; any other indicator is resolved from `macro_indicators`.

Backtests accept an optional `benchmark_ticker` (default `SPY`). When benchmark
prices are stored for the same date range, the response includes
`benchmark_return` and `excess_return`; previous runs can be retrieved from
`GET /api/v1/backtest/history`.

SEC submissions can be queried with
`GET /api/v1/ai/sec/{ticker}?start=YYYY-MM-DD&end=YYYY-MM-DD`. The endpoint
uses SEC's public submissions feed and applies the same optional FinBERT
sentiment engine to the filing metadata. Full filing text extraction and
persistent filing storage remain a next-stage item.
