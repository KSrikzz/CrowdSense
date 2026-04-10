import { useState, useEffect, useRef } from "react";

export default function AlertPanel({ alerts }) {
  const [log, setLog] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (alerts.length > 0) {
      setLog(prev => {
        const entries = alerts.map(a => ({
          ...a,
          id: `${a.zone}-${Date.now()}-${Math.random()}`,
          time: new Date().toLocaleTimeString(),
        }));
        return [...prev, ...entries].slice(-30); // Keep last 30
      });
    }
  }, [alerts]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [log]);

  const colorMap = {
    SAFE:     "#00ff88",
    WATCH:    "#ffd200",
    WARNING:  "#ff8800",
    EVACUATE: "#ff2222",
  };

  const bgMap = {
    SAFE:     "#002a1a",
    WATCH:    "#2a2000",
    WARNING:  "#2a1000",
    EVACUATE: "#2a0000",
  };

  return (
    <div style={{ background:"#0f1629", border:"1px solid #1e2a4a",
                  borderRadius:"10px", padding:"12px", flex:1 }}>
      <div style={{ fontSize:"12px", color:"#5577aa", marginBottom:"10px",
                    display:"flex", justifyContent:"space-between" }}>
        <span>🚨 Officer Alert Log</span>
        <span style={{ color: alerts.length > 0 ? "#ff8800" : "#2a3a5a" }}>
          {alerts.length > 0 ? `${alerts.length} ACTIVE` : "ALL CLEAR"}
        </span>
      </div>

      <div ref={scrollRef} style={{ height:"280px", overflowY:"auto", display:"flex",
                    flexDirection:"column", gap:"6px" }}>
        {log.length === 0 ? (
          <div style={{ textAlign:"center", color:"#2a3a5a", marginTop:"60px", fontSize:"13px" }}>
            <div style={{ fontSize:"28px", marginBottom:"8px" }}>✅</div>
            No alerts — all zones safe
          </div>
        ) : (
          log.map((a) => (
            <div key={a.id}
              style={{ background: bgMap[a.risk_level] || "#001a0a",
                       border:`1px solid ${colorMap[a.risk_level] || "#00ff88"}`,
                       borderRadius:"6px", padding:"8px 10px", fontSize:"11px",
                       animation:"fadeIn 0.3s ease" }}>
              <div style={{ display:"flex", justifyContent:"space-between",
                            marginBottom:"3px" }}>
                <span style={{ color: colorMap[a.risk_level], fontWeight:"700" }}>
                  {a.risk_level === "EVACUATE" ? "🔴" :
                   a.risk_level === "WARNING"  ? "🟠" :
                   a.risk_level === "WATCH"    ? "🟡" : "🟢"} Zone {a.zone}
                </span>
                <span style={{ color:"#3a4a6a", fontSize:"10px" }}>{a.time}</span>
              </div>
              <div style={{ color:"#aabbcc", lineHeight:"1.4" }}>{a.officer_action}</div>
              <div style={{ marginTop:"4px", display:"flex", gap:"8px", color:"#4a5a7a", fontSize:"10px" }}>
                <span>Score: {a.risk_score}</span>
                <span>👥 {a.person_count} persons</span>
              </div>
            </div>
          ))
        )}

      </div>

      <style>{`
        @keyframes fadeIn { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:#0a0e1e; }
        ::-webkit-scrollbar-thumb { background:#1e2a4a; border-radius:2px; }
      `}</style>
    </div>
  );
}
