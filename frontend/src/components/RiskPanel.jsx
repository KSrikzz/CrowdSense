export default function RiskPanel({ risks, forecasts }) {
  const levelColor = {
    SAFE: "var(--green)", WATCH: "var(--yellow)",
    WARNING: "var(--orange)", EVACUATE: "var(--red)"
  };
  const trendIcon = { RISING: "↑", FALLING: "↓", STABLE: "→" };
  const trendColor = { RISING: "var(--red)", FALLING: "var(--green)", STABLE: "var(--muted)" };

  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 10, overflow: "hidden"
    }}>
      <div style={{ padding: "8px 14px", borderBottom: "1px solid var(--border)" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", letterSpacing: 1 }}>
          STAMPEDE RISK SCORES
        </span>
      </div>
      <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        {(risks || []).map(r => {
          const color = levelColor[r.risk_level];
          const forecast = forecasts?.[r.zone];
          const trend = forecast?.trend;

          return (
            <div key={r.zone} style={{
              background: "var(--surface2)", borderRadius: 8, padding: "10px 12px",
              border: `1px solid ${color}35`,
            }}>
              {/* Zone header */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontWeight: 800, fontSize: 14, color }}>{r.zone}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: "1px 8px", borderRadius: 999,
                    background: color + "20", color, border: `1px solid ${color}40`
                  }}>{r.risk_level}</span>
                  {trend && (
                    <span style={{ fontSize: 13, color: trendColor[trend], fontWeight: 800 }}>
                      {trendIcon[trend]} {trend}
                    </span>
                  )}
                </div>
                <span style={{ fontWeight: 900, fontSize: 20, color }}>{r.risk_score.toFixed(0)}</span>
              </div>

              {/* Risk score bar */}
              <div style={{ height: 6, background: "var(--bg)", borderRadius: 999, overflow: "hidden", marginBottom: 8 }}>
                <div style={{
                  height: "100%", borderRadius: 999,
                  width: `${r.risk_score}%`,
                  background: color,
                  transition: "width 0.4s ease",
                  boxShadow: `0 0 6px ${color}`,
                }} />
              </div>

              {/* Factor breakdown */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "4px 12px" }}>
                {Object.entries(r.factors).map(([key, val]) => {
                  const label = key.replace(/_score$/, "").replace(/_/g, " ").toUpperCase();
                  return (
                    <div key={key} style={{ display: "flex", justifyContent: "space-between", fontSize: 10 }}>
                      <span style={{ color: "var(--muted)" }}>{label}</span>
                      <span style={{ color: "var(--text)", fontWeight: 700 }}>{val}</span>
                    </div>
                  );
                })}
              </div>

              {/* Forecast */}
              {forecast && (
                <div style={{
                  marginTop: 8, padding: "4px 8px", borderRadius: 6,
                  background: "var(--bg)", fontSize: 11, color: "var(--muted)"
                }}>
                  📈 Forecast: <strong style={{ color: "var(--text)" }}>{forecast.predicted_count} persons</strong>
                  {" "}in ~30s
                  {" "}(<span style={{ color: trendColor[trend] }}>{forecast.delta > 0 ? "+" : ""}{forecast.delta}</span>)
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
