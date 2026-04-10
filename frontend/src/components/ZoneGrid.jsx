export default function ZoneGrid({ zoneRisks }) {
  const colorMap = {
    SAFE:     { bg:"#002a1a", border:"#00aa55", text:"#00ff88" },
    WATCH:    { bg:"#2a2000", border:"#ccaa00", text:"#ffd200" },
    WARNING:  { bg:"#2a1000", border:"#cc6600", text:"#ff8800" },
    EVACUATE: { bg:"#2a0000", border:"#cc0000", text:"#ff2222" },
  };

  // Sort by zone label so grid stays stable
  const sorted = [...zoneRisks].sort((a, b) => a.zone.localeCompare(b.zone));

  return (
    <div style={{ background:"#0f1629", border:"1px solid #1e2a4a",
                  borderRadius:"10px", padding:"12px" }}>
      <div style={{ fontSize:"12px", color:"#5577aa", marginBottom:"10px",
                    display:"flex", justifyContent:"space-between" }}>
        <span>📦 Zone Risk Grid (3×3)</span>
        <span style={{ color:"#2a3a5a" }}>live</span>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:"6px" }}>
        {sorted.map((z) => {
          const c  = colorMap[z.risk_level] || colorMap.SAFE;
          const pct = z.risk_score / 100;
          return (
            <div key={z.zone}
              style={{ background: c.bg, border:`1.5px solid ${c.border}`,
                       borderRadius:"8px", padding:"8px", textAlign:"center",
                       transition:"all 0.4s" }}>
              {/* Zone label */}
              <div style={{ fontSize:"11px", color:"#5577aa", marginBottom:"3px" }}>
                {z.zone}
              </div>
              {/* Risk score */}
              <div style={{ fontSize:"20px", fontWeight:"800", color: c.text }}>
                {z.risk_score.toFixed(0)}
              </div>
              {/* Progress bar */}
              <div style={{ height:"4px", background:"#1e2a4a", borderRadius:"2px",
                            marginTop:"5px", overflow:"hidden" }}>
                <div style={{ width:`${pct * 100}%`, height:"100%",
                              background: c.border, transition:"width 0.4s",
                              borderRadius:"2px" }} />
              </div>
              {/* Level badge */}
              <div style={{ fontSize:"9px", color: c.text, marginTop:"4px",
                            fontWeight:"700", letterSpacing:"0.5px" }}>
                {z.risk_level}
              </div>
              {/* Person count */}
              <div style={{ fontSize:"10px", color:"#4a5a7a", marginTop:"2px" }}>
                👥 {z.person_count}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div style={{ display:"flex", gap:"8px", marginTop:"10px", flexWrap:"wrap" }}>
        {[["SAFE","#00ff88"],["WATCH","#ffd200"],["WARNING","#ff8800"],["EVACUATE","#ff2222"]].map(([l,c]) => (
          <div key={l} style={{ display:"flex", alignItems:"center", gap:"4px", fontSize:"10px" }}>
            <div style={{ width:8, height:8, borderRadius:"50%", background:c }} />
            <span style={{ color:"#5577aa" }}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
