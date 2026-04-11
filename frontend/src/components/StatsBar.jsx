const RISK_COLORS = {
  SAFE: "#00ff88", WATCH: "#ffcc00", WARNING: "#ff8800", EVACUATE: "#ff3333",
};

function Card({ label, value, color = "#00dcff", pulse = false }) {
  return (
    <div style={{
      background: "#0f1629", border: "1px solid #1e2a4a",
      borderRadius: "10px", padding: "12px 16px", flex: 1,
      animation: pulse ? "pulseBorder 1.2s ease-in-out infinite" : "none",
    }}>
      <div style={{ fontSize: "10px", color: "#5577aa", marginBottom: "4px", fontWeight: 700 }}>
        {label}
      </div>
      <div style={{ fontSize: "22px", fontWeight: 800, color }}>{value}</div>
    </div>
  );
}

export default function StatsBar({
  highestRisk    = null,
  totalPeople    = 0,
  violating      = 0,
  jammedSections = 0,
}) {
  const level = highestRisk?.risk_level || "SAFE";
  const color = RISK_COLORS[level]      || "#00ff88";
  const isBad = level === "WARNING" || level === "EVACUATE";

  // Only show violating count when risk is not SAFE
  const displayViolating = level === "SAFE" ? 0 : violating;

  return (
    <>
      <style>{`
        @keyframes pulseBorder {
          0%,100% { box-shadow: 0 0 0 0 rgba(255,51,51,0); }
          50%      { box-shadow: 0 0 0 6px rgba(255,51,51,0.25); }
        }
      `}</style>
      <div style={{ display:"flex", gap:"10px", marginTop:"12px", flexWrap:"wrap" }}>
        <Card label="👥 PEOPLE DETECTED" value={totalPeople}                color="#00dcff" />
        <Card label="⚠️ PEOPLE AT RISK"  value={displayViolating}           color={displayViolating > 0 ? "#ff8800" : "#00ff88"} />
        <Card label="🔴 JAMMED ZONES"    value={`${jammedSections}/9`}      color={jammedSections > 0 ? color : "#00ff88"} />
        <Card label="🚨 RISK LEVEL"      value={level}                      color={color} pulse={isBad} />
      </div>
    </>
  );
}