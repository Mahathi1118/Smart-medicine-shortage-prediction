"""Demand forecasting and shortage-risk estimation."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

HORIZON_DAYS = 14


def _features(t, dow):
    """Trend + weekly seasonality features."""
    t = np.asarray(t, dtype=float)
    dow = np.asarray(dow, dtype=float)
    return np.column_stack([t, np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)])


def forecast_daily(history, horizon=HORIZON_DAYS, window=60):
    """Forecast daily demand for the next `horizon` days.

    history: pandas Series of daily units used, indexed by DatetimeIndex.
    Returns a numpy array of non-negative predicted daily demand.
    """
    history = history.sort_index().iloc[-window:]
    t = np.arange(len(history))
    model = LinearRegression().fit(_features(t, history.index.dayofweek), history.values)
    future = pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=horizon)
    t_future = np.arange(len(history), len(history) + horizon)
    pred = model.predict(_features(t_future, future.dayofweek))
    return np.clip(pred, 0, None)


def risk_level(days_of_stock, lead_time_days):
    """HIGH: stock ends before a new supply can arrive. MEDIUM: very thin buffer."""
    if days_of_stock < lead_time_days:
        return "HIGH"
    if days_of_stock < lead_time_days + 5:
        return "MEDIUM"
    return "LOW"


def predict_all(consumption, inventory, as_of=None):
    """Forecast demand and shortage risk for every hospital-medicine pair."""
    c = consumption.copy()
    c["date"] = pd.to_datetime(c["date"])
    inv = inventory.copy()
    inv["expiry_date"] = pd.to_datetime(inv["expiry_date"])
    if as_of is None:
        as_of = c["date"].max() + pd.Timedelta(days=1)
    as_of = pd.Timestamp(as_of)

    rows = []
    for r in inv.itertuples():
        hist = c[(c.hospital_id == r.hospital_id) & (c.medicine == r.medicine)]
        hist = hist.set_index("date")["units_used"]
        f = forecast_daily(hist)
        avg = float(f.mean())
        days_of_stock = float(r.stock) / avg if avg > 0 else 999.0
        rows.append({
            "hospital_id": str(r.hospital_id),
            "medicine": str(r.medicine),
            "stock": int(r.stock),
            "avg_daily_forecast": round(avg, 1),
            "forecast_14d": round(float(f.sum()), 1),
            "days_of_stock": round(days_of_stock, 1),
            "lead_time_days": int(r.lead_time_days),
            "risk": risk_level(days_of_stock, int(r.lead_time_days)),
            "expiry_date": r.expiry_date.strftime("%Y-%m-%d"),
            "days_to_expiry": int((r.expiry_date - as_of).days),
        })
    return pd.DataFrame(rows)
