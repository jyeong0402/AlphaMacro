"""Pandas and NumPy backtesting engine."""
import operator
import numpy as np
import pandas as pd

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}

def buy_and_hold(data: pd.DataFrame, initial_capital: float) -> dict:
    """Calculate a benchmark return using the first open and last close."""
    if data.empty or len(data) < 2:
        raise ValueError("At least two price rows are required")
    frame = data.sort_index()
    entry = float(frame.iloc[0]["open"])
    exit_price = float(frame.iloc[-1]["close"])
    if entry <= 0:
        raise ValueError("Benchmark entry price must be positive")
    final_value = initial_capital * exit_price / entry
    values = initial_capital * frame["close"].astype(float) / entry
    daily = values.pct_change().dropna()
    return {
        "final_value": float(final_value),
        "total_return": float(final_value / initial_capital - 1),
        "sharpe_ratio": float(np.sqrt(252) * daily.mean() / daily.std()) if daily.std() else 0.0,
    }

def run_backtest(data: pd.DataFrame, initial_capital: float, buy_conditions: list, sell_conditions: list,
                 commission_rate: float, slippage_rate: float) -> dict:
    if data.empty or len(data) < 2:
        raise ValueError("At least two price rows are required")
    frame = data.sort_index().copy()
    cash, shares, pending = initial_capital, 0.0, None
    trades, equity = [], []
    for i, (date, row) in enumerate(frame.iterrows()):
        if pending:
            side = pending
            raw = float(row["open"])
            price = raw * (1 + slippage_rate if side == "BUY" else 1 - slippage_rate)
            if side == "BUY" and cash > 0:
                commission = cash * commission_rate
                qty = max((cash - commission) / price, 0)
                shares, cash = qty, 0
            elif side == "SELL" and shares > 0:
                qty, commission = shares, shares * price * commission_rate
                cash, shares = qty * price - commission, 0
            else: commission, qty = 0, 0
            if qty:
                trades.append({"trade_date": date, "side": side, "price": price, "quantity": qty,
                               "commission": commission, "slippage": abs(raw-price)*qty})
            pending = None
        value = cash + shares * float(row["close"])
        equity.append({"date": str(date), "value": value})
        def conditions(items):
            return all(OPS[c["operator"]](float(row.get(c["indicator"], np.nan)), c["value"]) for c in items)
        if i < len(frame) - 1:
            if shares == 0 and conditions(buy_conditions): pending = "BUY"
            elif shares > 0 and conditions(sell_conditions): pending = "SELL"
    values = pd.Series([x["value"] for x in equity])
    total = values.iloc[-1] / initial_capital - 1
    years = max((frame.index[-1] - frame.index[0]).days / 365.25, 1 / 365.25)
    peaks = values.cummax()
    mdd = float((values / peaks - 1).min())
    daily = values.pct_change().dropna()
    sharpe = float(np.sqrt(252) * daily.mean() / daily.std()) if daily.std() else 0.0
    closed_trades = [trade for trade in trades if trade["side"] == "SELL"]
    return {"final_value": float(values.iloc[-1]), "total_return": float(total),
            "cagr": float((1 + total) ** (1 / years) - 1) if 1 + total > 0 else -1,
            "mdd": mdd, "sharpe_ratio": sharpe, "trade_count": len(trades),
            "closed_trade_count": len(closed_trades), "trades": trades, "equity_curve": equity}
