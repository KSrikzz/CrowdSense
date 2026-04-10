const LEVEL_STYLES = {
  SAFE:     { bg:"#001a0d", border:"#00aa5540", color:"#00ff88", label:"✅ SAFE"     },
  WATCH:    { bg:"#1a1500", border:"#ccaa0040", color:"#ffcc00", label:"👁 WATCH"    },
  WARNING:  { bg:"#1a0a00", border:"#ff660040", color:"#ff8800", label:"⚠️ WARNING"  },
  EVACUATE: { bg:"#1a0000", border:"#ff000060", color:"#ff3333", label:"🚨 EVACUATE" },
};

function Stat({ label, value, color = "#00dcff" }) {
  return (
    <div style={{
      background:"#0a0e1e", borderRadius:"8px",
      padding:"10px 14px", border:"1px solid #1e2a4a",
      display:"flex", justifyContent:"space-between", alignItems:"center",
    }}>
      <span style={{ fontSize:"11px", color:"#5577aa" }}>{label}</span>
      <span style={{ fontSize:"18px", fontWeight:800, color }}>{value}</span>
    </div>
  );
}

export default function ZoneGrid({ zoneRisks }) {
  const risk   = zoneRisks?.[0]   ?? null;
  const level  = risk?.risk_level ?? "SAFE";
  const s      = LEVEL_STYLES[level] ?? LEVEL_STYLES.SAFE;
  const jammed = risk?.jammed_sections  ?? 0;
  const atRisk = risk?.violating_people ?? 0;
  const dwell  = risk?.dwell_frames     ?? 0;

  return (
    <div style={{
      background:"#0f1629", border:"1px solid #1e2a4a",
      borderRadius:"10px", padding:"16px",
    }}>
      <div style={{
        background:s.bg, border:`2px solid ${s.border}`,
        borderRadius:"10px", padding:"18px",
        textAlign:"center", marginBottom:"12px",
        transition:"all 0.4s ease",
      }}>
        <div style={{ fontSize:"28px", fontWeight:900, color:s.color, letterSpacing:"2px" }}>
          {s.label}
        </div>
        <div style={{ fontSize:"11px", color:"#5577aa", marginTop:"5px" }}>
          {level === "SAFE"
            ? "No jammed zones detected"
            : `${jammed} zone${jammed > 1 ? "s" : ""} fully jammed — no escape space`}
        </div>
      </div>
      <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
        <Stat label="🔴 Jammed Zones"   value={`${jammed} / 9`} color={jammed > 0 ? s.color : "#00ff88"} />
        <Stat label="⚠️ People at Risk" value={atRisk}           color={atRisk > 0 ? "#ff8800" : "#00ff88"} />
        <Stat label="⏱ Dwell Duration"  value={`${dwell} frames`} color={dwell >= 10 ? "#ff4444" : "#ffcc00"} />
      </div>
    </div>
  );
}