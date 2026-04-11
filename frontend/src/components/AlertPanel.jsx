import { useState, useEffect, useRef } from "react";

const LEVEL_COLOR = {
  WATCH:    "#ffd200",
  WARNING:  "#ff8800",
  EVACUATE: "#ff2222",
};

const LEVEL_BG = {
  WATCH:    "#1a1400",
  WARNING:  "#1a0900",
  EVACUATE: "#1a0000",
};

const LEVEL_ICON = {
  WATCH:    "🟡",
  WARNING:  "🟠",
  EVACUATE: "🔴",
};

export default function AlertPanel({ alerts }) {
  const [log, setLog]               = useState([]);
  const [isClearing, setIsClearing] = useState(false);
  const lastLevelRef                = useRef(null);
  const clearTimerRef               = useRef(null);
  const scrollRef                   = useRef(null);

  useEffect(() => {
    const active = (alerts || []).filter(a => a.level && a.level !== "SAFE");

    if (active.length === 0) {
      lastLevelRef.current = null;
      if (log.length > 0) {
        setIsClearing(true);
        clearTimerRef.current = setTimeout(() => {
          setLog([]);
          setIsClearing(false);
        }, 2500);
      }
      return;
    }

    if (clearTimerRef.current) {
      clearTimeout(clearTimerRef.current);
      clearTimerRef.current = null;
      setIsClearing(false);
    }

    const topAlert = active[0];
    if (topAlert.level === lastLevelRef.current) return;
    lastLevelRef.current = topAlert.level;

    const entry = {
      id:      `${topAlert.zone}-${Date.now()}`,
      level:   topAlert.level,
      zone:    topAlert.zone    || "FULL_FRAME",
      message: topAlert.message || "",
      count:   topAlert.count   || 0,
      time:    new Date().toLocaleTimeString(),
    };

    setLog(prev => [entry, ...prev].slice(0, 50));
  }, [alerts]);

  useEffect(() => () => clearTimeout(clearTimerRef.current), []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [log]);

  const activeLevel = (alerts || []).find(a => a.level && a.level !== "SAFE")?.level ?? null;
  const activeCount = (alerts || []).filter(a => a.level && a.level !== "SAFE").length;
  const borderColor = activeLevel
    ? LEVEL_COLOR[activeLevel]
    : isClearing ? "#00ff88" : "#1e2a4a";

  // ── What to show inside the log area ──────────────────────────
  // Priority: active entries > clearing banner > empty state
  const showEntries  = activeCount > 0;          // alerts firing right now
  const showClearing = !showEntries && isClearing; // just went safe, 2.5s banner
  const showEmpty    = !showEntries && !isClearing && log.length === 0; // truly idle

  return (
    <div style={{
      background:   "#0f1629",
      border:       `1px solid ${borderColor}`,
      borderRadius: "10px",
      padding:      "12px",
      flex:         1,
      transition:   "border-color 0.6s ease",
    }}>

      {/* ── Header ── */}
      <div style={{
        fontSize:       "12px",
        color:          "#5577aa",
        marginBottom:   "10px",
        display:        "flex",
        justifyContent: "space-between",
        alignItems:     "center",
      }}>
        <span>🚨 Officer Alert Log</span>
        <span style={{
          color:      activeCount > 0
                        ? LEVEL_COLOR[activeLevel]
                        : isClearing ? "#00ff88" : "#2a9a4a",
          fontWeight: "700",
          fontSize:   "11px",
          transition: "color 0.4s ease",
        }}>
          {activeCount > 0
            ? `${activeCount} ACTIVE`
            : isClearing ? "⬇️ THREAT CLEARED" : "✅ ALL CLEAR"}
        </span>
      </div>

      {/* ── Log area ── */}
      <div
        ref={scrollRef}
        style={{
          height:        "280px",
          overflowY:     "auto",
          display:       "flex",
          flexDirection: "column",
          gap:           "6px",
        }}
      >
        {/* CASE 1: active alerts — show log entries only */}
        {showEntries && log.map((a) => (
          <div
            key={a.id}
            style={{
              background:   LEVEL_BG[a.level]    || "#001a0a",
              border:       `1px solid ${LEVEL_COLOR[a.level] || "#00ff88"}`,
              borderRadius: "6px",
              padding:      "8px 10px",
              fontSize:     "11px",
              animation:    "fadeIn 0.3s ease",
            }}
          >
            <div style={{
              display:        "flex",
              justifyContent: "space-between",
              alignItems:     "center",
              marginBottom:   "4px",
            }}>
              <span style={{
                color:         LEVEL_COLOR[a.level],
                fontWeight:    "700",
                fontSize:      "12px",
                letterSpacing: "0.5px",
              }}>
                {LEVEL_ICON[a.level]} {a.level}
              </span>
              <span style={{ color: "#3a4a6a", fontSize: "10px" }}>{a.time}</span>
            </div>

            <div style={{ color: "#ccd6f6", lineHeight: "1.5", fontSize: "11px" }}>
              {a.message}
            </div>

            <div style={{
              marginTop: "5px",
              display:   "flex",
              gap:       "10px",
              color:     "#4a5a7a",
              fontSize:  "10px",
            }}>
              <span>📍 {a.zone.replace(/_/g, " ")}</span>
              <span>👥 {a.count} people</span>
            </div>
          </div>
        ))}

        {/* CASE 2: just cleared — green banner for 2.5s, no old entries */}
        {showClearing && (
          <div style={{
            background:   "#001a0a",
            border:       "1px solid #00ff88",
            borderRadius: "6px",
            padding:      "10px 12px",
            display:      "flex",
            alignItems:   "center",
            gap:          "8px",
            animation:    "fadeIn 0.4s ease",
          }}>
            <span style={{ fontSize: "18px" }}>✅</span>
            <div>
              <div style={{ color: "#00ff88", fontWeight: "700", fontSize: "12px" }}>
                AREA CLEARED
              </div>
              <div style={{ color: "#4a8a6a", fontSize: "10px", marginTop: "2px" }}>
                All zones returned to safe levels
              </div>
            </div>
            <span style={{ marginLeft: "auto", color: "#2a4a3a", fontSize: "10px" }}>
              {new Date().toLocaleTimeString()}
            </span>
          </div>
        )}

        {/* CASE 3: truly idle — no alerts ever or fully reset */}
        {showEmpty && (
          <div style={{
            textAlign:  "center",
            color:      "#2a3a5a",
            marginTop:  "60px",
            fontSize:   "13px",
          }}>
            <div style={{ fontSize: "28px", marginBottom: "8px" }}>✅</div>
            No alerts — all zones clear
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0a0e1e; }
        ::-webkit-scrollbar-thumb { background: #1e2a4a; border-radius: 2px; }
      `}</style>
    </div>
  );
}