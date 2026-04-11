from collections import deque

_risk_history: deque = deque(maxlen=30)


def get_all_risks(proximity_result: dict, conflict: float = 0.0) -> list:
    risk_level     = proximity_result.get("risk_level", "SAFE")
    jammed         = proximity_result.get("jammed_sections", 0)
    violating      = proximity_result.get("violating_people", 0)
    dwell_frames   = proximity_result.get("dwell_frames", 0)
    dwell_seconds  = proximity_result.get("dwell_seconds", 0.0)
    total          = proximity_result.get("total_people", 0)
    density_pct    = proximity_result.get("density_pct", 0.0)
    _risk_history.append(risk_level)

    return [{
        "zone":             "FULL_FRAME",
        "risk_level":       risk_level,
        "count":            total,
        "jammed_sections":  jammed,
        "violating_people": violating,
        "dwell_frames":     dwell_frames,
        "dwell_seconds":    dwell_seconds,
        "density_pct":      density_pct,
    }]


def get_officer_alerts(all_risks: list) -> list:
    alerts = []
    for r in all_risks:
        level         = r.get("risk_level", "SAFE")
        if level == "SAFE":
            continue
        jammed        = r.get("jammed_sections", 0)
        dwell_seconds = r.get("dwell_seconds", 0.0)
        vp            = r.get("violating_people", 0)
        total         = r.get("count", 0)
        density_pct   = r.get("density_pct", 0.0)
        vp_pct        = round((vp / max(1, total)) * 100)

        msg = {
            "WATCH": (
                f"👁  WATCH  |  {vp} of {total} people too close"
                f"  ({vp_pct}% of crowd)  |  Monitor zone"
            ),
            "WARNING": (
                f"⚠️  WARNING  |  {jammed} zone(s) jammed"
                f"  ·  {vp} people trapped  ({vp_pct}%)"
                f"  ·  No exit visible  |  Dispatch officer"
            ),
            "EVACUATE": (
                f"🚨  EVACUATE  |  {jammed} zone(s) critical"
                f"  ·  {vp}/{total} people locked in"
                f"  ·  Jammed {dwell_seconds}s  ·  Density {density_pct}%"
                f"  |  CLEAR AREA NOW"
            ),
        }.get(level, "")
        if msg:
            alerts.append({
                "zone":    r.get("zone", "FULL_FRAME"),
                "level":   level,
                "message": msg,
                "count":   total,
            })
    return alerts


def reset_density_history():
    _risk_history.clear()