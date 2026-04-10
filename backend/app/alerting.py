"""
CrowdSense AI — Alerting Engine
=================================
Manages alert state, cooldowns, escalation logic,
and alert history log for the officer dashboard.

Cooldowns:
  WATCH    → 10s
  WARNING  → 5s
  EVACUATE → 3s (near-continuous)
"""

from datetime import datetime, timedelta
from collections import deque
import threading

COOLDOWN = {
    "WATCH":    timedelta(seconds=10),
    "WARNING":  timedelta(seconds=5),
    "EVACUATE": timedelta(seconds=3),
}

MAX_LOG = 200

_alert_log:    deque = deque(maxlen=MAX_LOG)
_last_alerted: dict  = {}
_lock = threading.Lock()


def _should_alert(zone: str, level: str) -> bool:
    if level == "SAFE":
        return False
    now      = datetime.now()
    cooldown = COOLDOWN.get(level, timedelta(seconds=5))
    last     = _last_alerted.get(zone)
    return last is None or (now - last) >= cooldown


def _format_alert(risk: dict) -> dict:
    return {
        "id":             f"{risk['zone']}-{datetime.now().strftime('%H%M%S%f')}",
        "zone":           risk["zone"],
        "risk_level":     risk["risk_level"],
        "risk_score":     risk["risk_score"],
        "person_count":   risk["person_count"],
        "officer_action": risk["officer_action"],
        "color":          risk["color"],
        "timestamp":      datetime.now().isoformat(),
        "factors":        risk.get("factors", {}),
    }


def process_alerts(risks: list) -> list:
    new_alerts = []
    now        = datetime.now()
    with _lock:
        for risk in risks:
            zone  = risk["zone"]
            level = risk["risk_level"]
            if not _should_alert(zone, level):
                continue
            alert = _format_alert(risk)
            _alert_log.append(alert)
            _last_alerted[zone] = now
            new_alerts.append(alert)
            prefix = {"WATCH": "⚠️  WATCH", "WARNING": "🟠 WARNING",
                      "EVACUATE": "🔴 EVACUATE"}.get(level, "")
            print(f"[ALERT] {prefix} | Zone {zone} | "
                  f"Score: {risk['risk_score']} | "
                  f"People: {risk['person_count']} | "
                  f"{risk['officer_action']}")
    return new_alerts


def get_alert_history(limit: int = 50) -> list:
    with _lock:
        return list(reversed(list(_alert_log)))[:limit]


def get_alert_stats() -> dict:
    with _lock:
        log = list(_alert_log)
    stats = {"WATCH": 0, "WARNING": 0, "EVACUATE": 0, "total": len(log)}
    for a in log:
        level = a.get("risk_level")
        if level in stats:
            stats[level] += 1
    return stats


def get_active_zones() -> list:
    cutoff = datetime.now() - timedelta(seconds=30)
    with _lock:
        return [z for z, ts in _last_alerted.items() if ts >= cutoff]


def reset_alerts():
    global _alert_log, _last_alerted
    with _lock:
        _alert_log.clear()
        _last_alerted.clear()