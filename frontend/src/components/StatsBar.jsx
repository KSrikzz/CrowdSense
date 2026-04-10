export default function StatsBar({ totalPeople, flowConflict, avgSpeed, highestRisk, alertCount }) {
  const riskColor = highestRisk
    ? { SAFE:"#00ff88", WATCH:"#ffd200", WARNING:"#ff8800", EVACUATE:"#ff2222" }
      [highestRisk.risk_level] : "#00ff88";

  const stats = [
    { label:"👥 Total People",    value: totalPeople,                        unit:"" },
    { label:"📊 Highest Risk",    value: highestRisk?.risk_score?.toFixed(1) ?? "—", unit:"/100", color: riskColor },
    { label:"⚠️ Active Alerts",   value: alertCount,                         unit:"",  color: alertCount > 0 ? "#ff8800" : "#00ff88" },
    { label:"💨 Crowd Speed",     value: avgSpeed.toFixed(2),                unit:" px/f" },
    { label:"⚡ Flow Conflict",   value: (flowConflict * 100).toFixed(1),    unit:"%" },
    { label:"🔴 Risk Level",      value: highestRisk?.risk_level ?? "SAFE",  unit:"",  color: riskColor },
  ];

  return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:"8px" }}>
      {stats.map((s, i) => (
        <div key={i} style={{ background:"#0f1629", border:"1px solid #1e2a4a",
                              borderRadius:"8px", padding:"10px 12px" }}>
          <div style={{ fontSize:"10px", color:"#5577aa", marginBottom:"4px" }}>{s.label}</div>
          <div style={{ fontSize:"20px", fontWeight:"700",
                        color: s.color || "#00dcff" }}>{s.value}
            <span style={{ fontSize:"11px", color:"#5577aa" }}>{s.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
