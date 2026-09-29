"""Macro correlation and technical indicator calculations."""
import numpy as np
import pandas as pd

def daily_returns(values: pd.Series) -> pd.Series:
    return values.astype(float).pct_change().replace([np.inf, -np.inf], np.nan)

def rsi(values: pd.Series, period: int = 14) -> pd.Series:
    delta = values.astype(float).diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

def macd(values: pd.Series) -> tuple[pd.Series, pd.Series]:
    line = values.astype(float).ewm(span=12, adjust=False).mean() - values.astype(float).ewm(span=26, adjust=False).mean()
    return line, line.ewm(span=9, adjust=False).mean()

def correlation(stock: pd.Series, indicator: pd.Series, use_returns: bool = True) -> dict:
    stock = daily_returns(stock) if use_returns else stock
    indicator = daily_returns(indicator) if use_returns else indicator
    joined = pd.concat([stock.rename("stock"), indicator.rename("indicator")], axis=1).dropna()
    return {"value": float(joined["stock"].corr(joined["indicator"])) if len(joined) >= 2 else None,
            "stock": joined["stock"].tolist(), "indicator": joined["indicator"].tolist(),
            "dates": [str(x) for x in joined.index]}
