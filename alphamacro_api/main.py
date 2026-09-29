"""FastAPI application entry point."""
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from . import models
from .core.redis import ping
from .core.config import settings
from .routers import auth, macro, ai, backtest, user, alerts
from .tasks.data_refresh import refresh_loop
from .services.alert_evaluator import evaluate_alerts
from .database import SessionLocal
import logging

logger = logging.getLogger(__name__)


async def alert_loop(stop_event: asyncio.Event) -> None:
    interval = max(settings.alert_check_interval_seconds, 5)
    while not stop_event.is_set():
        try:
            with SessionLocal() as db:
                await evaluate_alerts(db)
        except Exception:
            logger.exception("Alert evaluation failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    stop_event = asyncio.Event()
    refresh_task = asyncio.create_task(refresh_loop(stop_event)) if settings.refresh_enabled else None
    alert_task = asyncio.create_task(alert_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        if refresh_task:
            await refresh_task
        await alert_task

app = FastAPI(title="AlphaMacro API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(macro.router, prefix="/api/v1/macro", tags=["macro"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(user.router, prefix="/api/v1/user", tags=["user"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
# Keep the original alert URLs available for existing clients.
app.include_router(alerts.router, prefix="/api/v1/user/alerts", tags=["alerts"])

@app.get("/health")
def health():
    return {"status": "ok", "redis": ping()}
