export default function VideoFeed({ frame, connected, sourceReady }) {
  return (
    <div style={{ background:"#0f1629", border:"1px solid #1e2a4a",
                  borderRadius:"10px", overflow:"hidden" }}>
      <div style={{ padding:"8px 12px", borderBottom:"1px solid #1e2a4a",
                    fontSize:"12px", color:"#5577aa", display:"flex",
                    justifyContent:"space-between" }}>
        <span>🎥 Live Heatmap Feed</span>
        <span style={{ color: connected ? "#00ff88" : "#ff4444" }}>
          {connected ? "● STREAMING" : "● WAITING"}
        </span>
      </div>
      {frame ? (
        <img
          src={`data:image/jpeg;base64,${frame}`}
          alt="Live heatmap"
          style={{ width:"100%", display:"block", maxHeight:"400px", objectFit:"cover" }}
        />
      ) : (
        <div style={{ height:"360px", display:"flex", alignItems:"center",
                      justifyContent:"center", color:"#2a3a5a", flexDirection:"column", gap:"10px" }}>
          <div style={{ fontSize:"40px" }}>📷</div>
          <div style={{ fontSize:"14px", color:"#5577aa" }}>
            {connected && sourceReady
              ? "Processing video source..."
              : connected
              ? "No video source configured"
              : "Connecting to backend..."}
          </div>
          <div style={{ fontSize:"11px", color:"#3a4a6a" }}>
            {!sourceReady
              ? "Use the controls above to upload a video or start your webcam"
              : "Stream will appear shortly"}
          </div>
        </div>
      )}
    </div>
  );
}
