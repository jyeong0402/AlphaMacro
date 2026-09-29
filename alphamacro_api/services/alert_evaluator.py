"""Evaluate persisted user alerts against the latest stored market data."""
from __future__ import annotations

import operator
from datetime import date
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MacroIndicator, StockPrice, UserAlert
from ..core.events import publish_alert

logger = logging.getLogger(__name__)
OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}
_triggered: set[tuple[int, date]] = set()


def _latest_metric(db: Session, ticker: str, indicator: str) -> tuple[date, float] | None:
    stock = db.scalar(
        select(StockPrice)
        .where(StockPrice.ticker == ticker)
        .order_by(StockPrice.date.desc())
    )
    if not stock:
        return None
    values = {
        "OPEN": stock.open_price,
        "HIGH": stock.high_price,
        "LOW": stock.low_price,
        "CLOSE": stock.close_price,
        "PRICE": stock.close_price,
        "RSI": stock.rsi_14,
        "RSI_14": stock.rsi_14,
        "MACD": stock.macd,
        "MACD_SIGNAL": stock.macd_signal,
    }
    normalized = indicator.strip().upper()
    if normalized in values:
        value = values[normalized]
        return (stock.date, float(value)) if value is not None else None

    macro = db.scalar(
        select(MacroIndicator)
        .where(
            MacroIndicator.indicator == indicator,
            MacroIndicator.date <= stock.date,
        )
        .order_by(MacroIndicator.date.desc())
    )
    return (macro.date, float(macro.value)) if macro else None


async def evaluate_alerts(db: Session) -> int:
    """Publish one event when an enabled condition first becomes true per day."""
    triggered = 0
    alerts = db.scalars(select(UserAlert).where(UserAlert.enabled.is_(True))).all()
    for alert in alerts:
        condition = alert.condition or {}
        ticker = str(condition.get("ticker", "")).strip().upper()
        indicator = str(condition.get("indicator", "")).strip()
        operator_name = condition.get("operator")
        try:
            threshold = float(condition["value"])
            compare = OPERATORS[operator_name]
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping invalid alert condition for alert_id=%s", alert.id)
            continue
        if not ticker or not indicator:
            logger.warning("Skipping incomplete alert condition for alert_id=%s", alert.id)
            continue
        metric = _latest_metric(db, ticker, indicator)
        if not metric:
            continue
        metric_date, current_value = metric
        key = (alert.id, metric_date)
        if compare(current_value, threshold):
            if key in _triggered:
                continue
            _triggered.add(key)
            await publish_alert({
                "type": "alert.triggered",
                "user_id": alert.user_id,
                "alert_id": alert.id,
                "name": alert.name,
                "ticker": ticker,
                "indicator": indicator,
                "value": current_value,
                "operator": operator_name,
                "threshold": threshold,
                "date": metric_date.isoformat(),
            })
            triggered += 1
        else:
            _triggered.discard(key)
    return triggered
