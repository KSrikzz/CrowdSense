import { useState, useEffect, useRef, useCallback } from "react";
import SourceControls from "./components/SourceControls.jsx";
import VideoFeed from "./components/VideoFeed.jsx";
import ZoneGrid from "./components/ZoneGrid.jsx";
import AlertPanel from "./components/AlertPanel.jsx";
import StatsBar from "./components/StatsBar.jsx";
import DensityChart from "./components/DensityChart.jsx";

const WS_URL = "ws://localhost:8000/ws/stream";

export default function App() {
  const [connected,    setConnected]    = useState(false);
  const [frame,        setFrame]        = useState(null);
  const [totalPeople,  setTotalPeople]  = useState(0);
  const [zoneRisks,    setZoneRisks]    = useState([]);
  const [alerts,       setAlerts]       = useState([]);
  const [highestRisk,  setHighestRisk]  = useState(null);
  const [flowConflict, setFlowConflict] = useState(0);
  const [avgSpeed,     setAvgSpeed]     = useState(0);
  const [densityLog,   setDensityLog]   = useState([]);
  const [frameNo,      setFrameNo]      = useState(0);
  const [sourceReady,  setSourceReady]  = useState(false);
  const wsRef = useRef(null);

  /* ── WebSocket connect / reconnect ── */
  const connect = useCallback(() => {
    // Close any existing connection first
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen  = () => setConnected(true);
    ws.onclose = () => { setConnected(false); };
    ws.onerror = () => { setConnected(false); };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.error) { console.error(data.error); return; }

      setFrame(data.frame);
      setTotalPeople(data.total_people   || 0);
      setZoneRisks(data.stampede_risks   || []);
      setAlerts(data.officer_alerts      || []);
      setHighestRisk(data.highest_risk   || null);
      setFlowConflict(data.flow_conflict || 0);
      setAvgSpeed(data.avg_speed         || 0);
      setFrameNo(data.frame_number       || 0);

      setDensityLog(prev => {
        const next = [...prev, { t: data.frame_number, v: data.total_people }];
        return next.slice(-60); // Keep last 60 readings
      });
    };
  }, []);

  /* ── Initial connect ── */
  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  /* ── Called when user uploads video or starts webcam ── */
  const handleSourceReady = useCallback(() => {
    setSourceReady(true);
    setFrame(null);
    setDensityLog([]);
    setFrameNo(0);
    setTotalPeople(0);
    setZoneRisks([]);
    setAlerts([]);
    setHighestRisk(null);
    setFlowConflict(0);
    setAvgSpeed(0);

    // Small delay to let the backend register the source, then reconnect WS
    setTimeout(() => {
      connect();
    }, 500);
  }, [connect]);

  /* ── Called when user clicks Stop — full reset to original state ── */
  const handleStop = useCallback(() => {
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    // Reset ALL state to initial values
    setConnected(false);
    setFrame(null);
    setTotalPeople(0);
    setZoneRisks([]);
    setAlerts([]);
    setHighestRisk(null);
    setFlowConflict(0);
    setAvgSpeed(0);
    setDensityLog([]);
    setFrameNo(0);
    setSourceReady(false);
  }, []);

  const bgColor = highestRisk
    ? { SAFE: "#0a0e1e", WATCH: "#1a1500", WARNING: "#1a0a00", EVACUATE: "#1a0000" }
      [highestRisk.risk_level] || "#0a0e1e"
    : "#0a0e1e";

  return (
    <div style={{ minHeight:"100vh", background: bgColor, transition:"background 1s", padding:"12px" }}>

      {/* ── Header ── */}
      <header style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                       marginBottom:"12px", borderBottom:"1px solid #1e2a4a", paddingBottom:"10px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
          <div style={{ width:10, height:10, borderRadius:"50%",
                        background: connected ? "#00ff88" : "#ff4444",
                        boxShadow: connected ? "0 0 8px #00ff88" : "none" }} />
          <span style={{ fontSize:"22px", fontWeight:"800", color:"#00dcff",
                         letterSpacing:"1px" }}>🎯 CrowdSense AI</span>
          <span style={{ fontSize:"11px", color:"#5577aa", marginLeft:"6px" }}>
            v2.0 — Stampede Prediction System
          </span>
        </div>
        <div style={{ display:"flex", gap:"20px", fontSize:"13px", color:"#5577aa" }}>
          <span>Frame #{frameNo}</span>
          <span style={{ color: connected ? "#00ff88" : "#ff4444" }}>
            {connected ? "🟢 LIVE" : "🔴 DISCONNECTED"}
          </span>
        </div>
      </header>

      {/* ── Source Controls (Upload / Webcam / Stop) ── */}
      <SourceControls onSourceReady={handleSourceReady} onStop={handleStop} connected={connected} />

      {/* ── Stats Bar ── */}
      <StatsBar
        totalPeople={totalPeople}
        flowConflict={flowConflict}
        avgSpeed={avgSpeed}
        highestRisk={highestRisk}
        alertCount={alerts.length}
      />

      {/* ── Main Grid ── */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 320px", gap:"12px", marginTop:"12px" }}>

        {/* Left: Video + Chart */}
        <div style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
          <VideoFeed frame={frame} connected={connected} sourceReady={sourceReady} />
          <DensityChart densityLog={densityLog} />
        </div>

        {/* Right: Zones + Alerts */}
        <div style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
          <ZoneGrid zoneRisks={zoneRisks} />
          <AlertPanel alerts={alerts} />
        </div>
      </div>
    </div>
  );
}
