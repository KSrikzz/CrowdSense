import { useEffect, useRef } from "react";

export default function AlertCards({ alerts }) {
  const prevCount = useRef(0);

  useEffect(() => {
    if (alerts?.length > prevCount.current) {
      // Play a beep for new alerts
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.value = 880;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        osc.start(); osc.stop(ctx.currentTime + 0.4);
      } catch (_) {}
    }
    prevCount.current = alerts?.length || 0;
  }, [alerts?.length]);

  const levelColor = {
    WATCH: "var(--yellow)", WARNING: "var(--orange)", EVACUATE: "var(--red)"
  };
  const levelIcon = {
    WATCH: "👁", WARNING: "⚠️", EVACUATE: "🚨"
  };

  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 10, overflow: "hidden"
    }}>
      <div style={{
        padding: "8px 14px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", letterSpacing: 1 }}>
          OFFICER ALERTS
        </span>
        {alerts?.length > 0 && (
          <span style={{
            background: "var(--red)25", color: "var(--red)",
            border: "1px solid var(--red)50",
            borderRadius: 999, padding: "1px 10px", fontSize: 11, fontWeight: 800
          }}>
            {alerts.length} ACTIVE
          </span>
        )}
      </div>

      <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8, maxHeight: 320, overflowY: "auto" }}>
        {(!alerts || alerts.length === 0) ? (
          <div style={{ textAlign: "center", padding: "24px 0", color: "var(--muted)" }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>✅</div>
            <div style={{ fontSize: 13 }}>All zones are SAFE</div>
            <div style={{ fontSize: 11, marginTop: 4, color: "var(--border)" }}>No officer action required</div>
          </div>
        ) : (
          alerts.map((alert, i) => {
            const color = levelColor[alert.risk_level] || "var(--yellow)";
            const icon  = levelIcon[alert.risk_level]  || "⚠️";
            return (
              <div key={i} style={{
                background: color + "12",
                border: `1px solid ${color}45`,
                borderRadius: 8, padding: "10px 14px",
                borderLeft: `4px solid ${color}`,
              }} className={alert.risk_level === "EVACUATE" ? "pulse-red" : ""}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 16 }}>{icon}</span>
                  <span style={{ fontWeight: 800, fontSize: 13, color }}>
                    Zone {alert.zone} — {alert.risk_level}
                  </span>
                  <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--muted)" }}>
                    Risk: {alert.risk_score.toFixed(0)}/100
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.5 }}>
                  {alert.officer_action}
                </div>
                <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 4 }}>
                  👥 {alert.person_count} persons detected
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
