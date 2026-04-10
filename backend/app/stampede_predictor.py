from collections import deque

_risk_history: deque = deque(maxlen=30)


def get_all_risks(proximity_result: dict, conflict: float = 0.0) -> list:
    risk_level = proximity_result.get("risk_level", "SAFE")
    jammed     = proximity_result.get("jammed_sections", 0)
    violating  = proximity_result.get("violating_people", 0)
    dwell      = proximity_result.get("dwell_frames", 0)
    total      = proximity_result.get("total_people", 0)
    _risk_history.append(risk_level)
    return [{
        "zone":             "FULL_FRAME",
        "risk_level":       risk_level,
        "count":            total,
        "jammed_sections":  jammed,
        "violating_people": violating,
        "dwell_frames":     dwell,
        "density_pct":      min(100, round((jammed/3)*100, 1)),
    }]


def get_officer_alerts(all_risks: list) -> list:
    alerts = []
    for r in all_risks:
        level  = r.get("risk_level", "SAFE")
        if level == "SAFE":
            continue
        jammed = r.get("jammed_sections", 0)
        dwell  = r.get("dwell_frames", 0)
        vp     = r.get("violating_people", 0)
        msg    = {
            "WATCH":    f"👁 Crowding detected — {vp} people with limited space",
            "WARNING":  f"⚠️ {jammed} zone(s) fully jammed — no escape route visible",
            "EVACUATE": f"🚨 CRITICAL — {jammed} zones jammed for {dwell} frames. Evacuate!",
        }.get(level, "")
        if msg:
            alerts.append({
                "zone":    r.get("zone", "FULL_FRAME"),
                "level":   level,
                "message": msg,
                "count":   r.get("count", 0),
            })
    return alerts


def reset_density_history():
    _risk_history.clear()