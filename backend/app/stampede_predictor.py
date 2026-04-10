"""
CrowdSense AI — Stampede Prediction Engine
============================================
Computes real-time Stampede Risk Score (0-100) per zone.

4-Factor Model:
  1. Density Score       (35%) — current person count
  2. Growth Rate Score   (30%) — how fast density is RISING
  3. Acceleration Score  (20%) — sudden panic surges
  4. Flow Conflict Score (15%) — people pushing against each other

Risk Levels:
  SAFE     (0-34)   — No action
  WATCH    (35-57)  — Deploy officers
  WARNING  (58-77)  — Intervene now, open exits
  EVACUATE (78-100) — Clear zone, stampede imminent
"""

from collections import deque
from datetime import datetime
import numpy as np

HISTORY_LIMIT   = 60
density_history: dict[str, deque] = {}


def _get_history(zone: str) -> deque:
    if zone not in density_history:
        density_history[zone] = deque(maxlen=HISTORY_LIMIT)
    return density_history[zone]


def record_density(zone: str, count: int):
    _get_history(zone).append({"count": count, "ts": datetime.now()})


def _density_score(count: int) -> float:
    """
    Realistic density thresholds:
      < 5  people → 0   (ignore near-empty zones)
      10   people → 12
      25   people → 31
      50   people → 62
      80+  people → 100
    """
    if count < 5:
        return 0.0
    return min(100.0, (count / 80.0) * 100.0)


def _growth_rate_score(zone: str) -> float:
    hist = list(_get_history(zone))
    if len(hist) < 5:
        return 0.0
    recent = [h["count"] for h in hist[-10:]]
    x      = np.arange(len(recent), dtype=float)
    slope  = float(np.polyfit(x, recent, 1)[0])
    return max(0.0, min(100.0, slope * 15.0))


def _acceleration_score(zone: str) -> float:
    hist = list(_get_history(zone))
    if len(hist) < 6:
        return 0.0
    counts    = [h["count"] for h in hist[-6:]]
    diffs     = np.diff(counts)
    accel     = np.diff(diffs)
    max_accel = float(np.max(accel)) if len(accel) > 0 else 0.0
    return max(0.0, min(100.0, max_accel * 20.0))


def _flow_conflict_score(conflict: float) -> float:
    return min(100.0, conflict * 100.0)


def compute_stampede_risk(zone: str, count: int, conflict: float = 0.0) -> dict:
    record_density(zone, count)

    d_score = _density_score(count)
    g_score = _growth_rate_score(zone)
    a_score = _acceleration_score(zone)
    f_score = _flow_conflict_score(conflict)

    composite = round(min(100.0,
        d_score * 0.35 +
        g_score * 0.30 +
        a_score * 0.20 +
        f_score * 0.15
    ), 1)

    if composite < 35:
        level  = "SAFE"
        action = f"No action required. Monitoring Zone {zone}."
        color  = "green"
    elif composite < 58:
        level  = "WATCH"
        action = f"Deploy officers to Zone {zone}. Monitor closely."
        color  = "yellow"
    elif composite < 78:
        level  = "WARNING"
        action = f"INTERVENE — Open exits and redirect crowd from Zone {zone}."
        color  = "orange"
    else:
        level  = "EVACUATE"
        action = f"IMMEDIATE EVACUATION — Clear Zone {zone}. Stampede imminent."
        color  = "red"

    return {
        "zone":           zone,
        "risk_score":     composite,
        "risk_level":     level,
        "color":          color,
        "officer_action": action,
        "person_count":   count,
        "factors": {
            "density_score":       round(d_score, 1),
            "growth_score":        round(g_score, 1),
            "acceleration_score":  round(a_score, 1),
            "flow_conflict_score": round(f_score, 1),
        },
        "timestamp": datetime.now().isoformat(),
    }


def get_all_risks(zone_counts: dict, conflict: float = 0.0) -> list:
    risks = [compute_stampede_risk(z, c, conflict)
             for z, c in zone_counts.items()]
    return sorted(risks, key=lambda x: x["risk_score"], reverse=True)


def get_officer_alerts(risks: list) -> list:
    return [r for r in risks if r["risk_level"] != "SAFE"]


def reset_density_history():
    global density_history
    density_history.clear()