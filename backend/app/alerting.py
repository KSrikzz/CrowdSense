from collections import deque
from datetime import datetime

ALERT_HISTORY_LIMIT = 100
_alert_history = deque(maxlen=ALERT_HISTORY_LIMIT)

_last_level = "SAFE"


def _format_alert(risk):
    return {
        "zone":       risk.get("zone", "FULL_FRAME"),
        "risk_level": risk.get("level") or risk.get("risk_level", "SAFE"),
        "message":    risk.get("message", "Crowd alert triggered."),
        "count":      risk.get("count", 0),
        "timestamp":  datetime.now().strftime("%H:%M:%S"),
    }


def process_alerts(risks):
    global _last_level

    new_alerts = []

    for risk in risks:
        level = risk.get("level") or risk.get("risk_level", "SAFE")

        if level == "SAFE":
            continue

        if level != _last_level:
            alert = _format_alert(risk)
            _alert_history.append(alert)
            new_alerts.append(alert)

        _last_level = level

    return new_alerts


def get_alert_history(limit=20):
    return list(_alert_history)[-limit:][::-1]


def get_alert_stats():
    history = list(_alert_history)
    return {
        "total_alerts": len(history),
        "warning_count": sum(1 for a in history if a["risk_level"] == "WARNING"),
        "evacuate_count": sum(1 for a in history if a["risk_level"] == "EVACUATE"),
        "watch_count": sum(1 for a in history if a["risk_level"] == "WATCH"),
    }


def reset_alerts():
    global _last_level
    _alert_history.clear()
    _last_level = "SAFE"