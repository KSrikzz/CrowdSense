import math
from collections import defaultdict

CLOSE_THRESHOLD    = 0.8   # was 1.5 — only flag truly packed crowds (< 0.8× avg height apart)
DWELL_MIN_FRAMES   = 12    # was 4  — must stay close for 12 frames (~0.4s) to count
GRID_ROWS          = 3
GRID_COLS          = 3
MIN_SECTION_PEOPLE = 3
JAM_RATIO          = 0.65

RISK_FROM_JAMMED   = {0: "SAFE", 1: "WATCH", 2: "WARNING", 3: "EVACUATE"}

_dwell_counters: dict = {}
_jammed_dwell:   dict = {}


def _norm_distance(p1, p2, h1, h2) -> float:
    dx, dy = p1[0]-p2[0], p1[1]-p2[1]
    return math.sqrt(dx*dx + dy*dy) / max(1, (h1+h2)/2.0)


def _get_section(anchor, fw, fh) -> int:
    col = min(int(anchor[0] / (fw / GRID_COLS)), GRID_COLS-1)
    row = min(int(anchor[1] / (fh / GRID_ROWS)), GRID_ROWS-1)
    return row * GRID_COLS + col


def _neighbors(sec_id) -> list:
    row, col = divmod(sec_id, GRID_COLS)
    out = []
    for dr in (-1,0,1):
        for dc in (-1,0,1):
            if dr==0 and dc==0: continue
            r2, c2 = row+dr, col+dc
            if 0<=r2<GRID_ROWS and 0<=c2<GRID_COLS:
                out.append(r2*GRID_COLS+c2)
    return out


def _empty_result(total=0):
    return {
        "jammed_sections":  0,
        "jammed_ids":       [],
        "violating_ids":    [],
        "violating_people": 0,
        "close_pair_count": 0,
        "dwell_frames":     0,
        "risk_level":       "SAFE",
        "total_people":     total,
        "section_counts":   {},
    }


def compute_proximity(ground_anchors: list, boxes: list,
                      frame_w: int = 1280, frame_h: int = 720) -> dict:
    global _dwell_counters, _jammed_dwell

    n = len(ground_anchors)
    if n < MIN_SECTION_PEOPLE:
        for p in list(_dwell_counters.keys()):
            _dwell_counters[p] = max(0, _dwell_counters[p] - 2)
            if _dwell_counters[p] == 0:
                del _dwell_counters[p]
        return _empty_result(n)

    heights = [max(1, abs(b[4]-b[2])) if len(b) >= 5 else 50 for b in boxes]
    while len(heights) < n:
        heights.append(50)

    # Step 1: Pairwise close check
    current_close = set()
    for i in range(n):
        for j in range(i+1, n):
            if _norm_distance(ground_anchors[i], ground_anchors[j],
                              heights[i], heights[j]) < CLOSE_THRESHOLD:
                current_close.add((i, j))

    # Step 2: Dwell counters
    for p in current_close:
        _dwell_counters[p] = _dwell_counters.get(p, 0) + 1
    for p in list(_dwell_counters.keys()):
        if p not in current_close:
            _dwell_counters[p] = max(0, _dwell_counters[p] - 1)
            if _dwell_counters[p] == 0:
                del _dwell_counters[p]

    confirmed_pairs = {p for p, d in _dwell_counters.items() if d >= DWELL_MIN_FRAMES}
    violating_ids   = {idx for pair in confirmed_pairs for idx in pair}

    # Step 3: Section map
    section_people = defaultdict(set)
    for idx, anchor in enumerate(ground_anchors):
        section_people[_get_section(anchor, frame_w, frame_h)].add(idx)
    section_counts = {s: len(ids) for s, ids in section_people.items()}

    # Step 4: Jam detection
    candidate_jammed = []
    for sec, ids in section_people.items():
        if len(ids) < MIN_SECTION_PEOPLE:
            continue
        close_in = sum(1 for idx in ids if idx in violating_ids)
        if (close_in / len(ids)) < JAM_RATIO:
            continue
        has_escape = any(
            section_counts.get(nb, 0) < MIN_SECTION_PEOPLE
            for nb in _neighbors(sec)
        )
        if not has_escape:
            candidate_jammed.append(sec)

    # Step 5: Jammed section dwell
    for s in candidate_jammed:
        _jammed_dwell[s] = _jammed_dwell.get(s, 0) + 1
    for s in list(_jammed_dwell.keys()):
        if s not in candidate_jammed:
            _jammed_dwell[s] = max(0, _jammed_dwell[s] - 2)
            if _jammed_dwell[s] == 0:
                del _jammed_dwell[s]

    confirmed_jammed = [s for s, d in _jammed_dwell.items() if d >= DWELL_MIN_FRAMES]
    jammed_count     = len(confirmed_jammed)
    risk_level       = RISK_FROM_JAMMED.get(min(jammed_count, 3), "EVACUATE")
    max_dwell        = max(_jammed_dwell.values(), default=0)

    return {
        "jammed_sections":  jammed_count,
        "jammed_ids":       confirmed_jammed,
        "violating_ids":    list(violating_ids),
        "violating_people": len(violating_ids),
        "close_pair_count": len(confirmed_pairs),
        "dwell_frames":     max_dwell,
        "risk_level":       risk_level,
        "total_people":     n,
        "section_counts":   section_counts,
    }


def reset_proximity():
    global _dwell_counters, _jammed_dwell
    _dwell_counters.clear()
    _jammed_dwell.clear()