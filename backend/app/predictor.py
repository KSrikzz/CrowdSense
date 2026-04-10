from collections import deque
from datetime import datetime
import numpy as np

HISTORY_LIMIT = 60
TREND_WINDOW  = 20
MIN_READINGS  = 10

zone_history: dict[str, deque] = {}


def record_zone(zone: str, count: int):
    if zone not in zone_history:
        zone_history[zone] = deque(maxlen=HISTORY_LIMIT)
    zone_history[zone].append({"count": count, "ts": datetime.now()})


def forecast_zone(zone: str, periods: int = 6) -> dict | None:
    """
    Forecast using linear regression (numpy.polyfit).
    Returns predicted_count, next_5_frames, trend, delta, slope, confidence (R²).
    Returns None if fewer than MIN_READINGS available.
    """
    records = list(zone_history.get(zone, []))
    if len(records) < MIN_READINGS:
        return None

    window = records[-TREND_WINDOW:]
    hist   = [r["count"] for r in window]
    n      = len(hist)
    x      = np.arange(n, dtype=np.float64)

    coeffs    = np.polyfit(x, hist, 1)
    slope     = float(coeffs[0])
    intercept = float(coeffs[1])

    forecast     = [max(0.0, intercept + slope * (n + i)) for i in range(1, periods + 1)]
    forecast_int = [round(v) for v in forecast]

    # R² confidence score
    y_pred = intercept + slope * x
    ss_res = float(np.sum((np.array(hist) - y_pred) ** 2))
    ss_tot = float(np.sum((np.array(hist) - np.mean(hist)) ** 2))
    r2     = round(max(0.0, min(1.0, 1.0 - (ss_res / (ss_tot + 1e-9)))), 3)

    delta = round(forecast[-1] - hist[-1], 1)
    trend = "RISING" if slope > 0.8 else "FALLING" if slope < -0.8 else "STABLE"

    return {
        "predicted_count": forecast_int[0],
        "next_5_frames":   forecast_int,
        "trend":           trend,
        "delta":           delta,
        "slope":           round(slope, 3),
        "confidence":      r2,
    }


def reset_forecast_history():
    global zone_history
    zone_history.clear()