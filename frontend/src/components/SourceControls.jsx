import { useState, useRef } from "react";

const API_BASE = "http://localhost:8000";

export default function SourceControls({ onSourceReady, onStop, connected }) {
  const [uploading, setUploading]       = useState(false);
  const [status, setStatus]             = useState(null);
  const [activeSource, setActiveSource] = useState(null);
  const fileRef = useRef(null);

  /* ── Upload a video file ── */
  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setStatus(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${API_BASE}/upload-video`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) throw new Error(`Upload failed (${res.status})`);

      const data = await res.json();
      setStatus({ type: "success", msg: `✅ ${data.message}` });
      setActiveSource("video");
      onSourceReady?.();
    } catch (err) {
      setStatus({ type: "error", msg: `❌ ${err.message}` });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  /* ── Use webcam / live feed ── */
  const handleWebcam = async () => {
    setStatus(null);
    try {
      const res = await fetch(`${API_BASE}/use-webcam`, { method: "POST" });
      if (!res.ok) throw new Error(`Webcam init failed (${res.status})`);

      const data = await res.json();
      setStatus({ type: "success", msg: `✅ ${data.message}` });
      setActiveSource("webcam");
      onSourceReady?.();
    } catch (err) {
      setStatus({ type: "error", msg: `❌ ${err.message}` });
    }
  };

  /* ── Stop streaming ── */
  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/stop`, { method: "POST" });
      setStatus({ type: "success", msg: "⏹ Stream stopped — all state reset" });
      setActiveSource(null);
      onStop?.();
    } catch (err) {
      setStatus({ type: "error", msg: `❌ ${err.message}` });
    }
  };

  /* ── Click the hidden file input programmatically ── */
  const triggerFileSelect = () => {
    fileRef.current?.click();
  };

  return (
    <div style={{
      background: "#0f1629",
      border: "1px solid #1e2a4a",
      borderRadius: "10px",
      padding: "14px 16px",
      marginBottom: "12px",
    }}>
      {/* ── Header ── */}
      <div style={{
        fontSize: "12px", color: "#5577aa", marginBottom: "12px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <span>🎬 Video Source Controls</span>
        {activeSource && (
          <span style={{
            fontSize: "10px", fontWeight: 700,
            padding: "2px 10px", borderRadius: "999px",
            background: activeSource === "webcam" ? "#00aa5520" : "#0066ff20",
            color: activeSource === "webcam" ? "#00ff88" : "#00aaff",
            border: `1px solid ${activeSource === "webcam" ? "#00aa5540" : "#0066ff40"}`,
            letterSpacing: "0.5px",
          }}>
            {activeSource === "webcam" ? "📷 WEBCAM ACTIVE" : "📁 VIDEO LOADED"}
          </span>
        )}
      </div>

      {/* ── Hidden file input ── */}
      <input
        ref={fileRef}
        type="file"
        accept="video/*,.mp4,.avi,.mov,.mkv"
        onChange={handleUpload}
        style={{ display: "none" }}
      />

      {/* ── Actions Row ── */}
      <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
        {/* Upload Video */}
        <button
          onClick={triggerFileSelect}
          disabled={uploading}
          style={{
            border: "1px dashed #2a3a5a",
            borderRadius: "8px",
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            cursor: uploading ? "not-allowed" : "pointer",
            letterSpacing: "0.5px",
            transition: "all 0.25s ease",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "transparent",
            color: "#5577aa",
            opacity: uploading ? 0.5 : 1,
          }}
        >
          <span>📁</span>
          <span>{uploading ? "Uploading..." : "Upload Video"}</span>
        </button>

        {/* Live Webcam */}
        <button
          onClick={handleWebcam}
          style={{
            border: "none",
            borderRadius: "8px",
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            cursor: "pointer",
            letterSpacing: "0.5px",
            transition: "all 0.25s ease",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: activeSource === "webcam"
              ? "linear-gradient(135deg, #00cc66 0%, #009944 100%)"
              : "linear-gradient(135deg, #00aa55 0%, #007733 100%)",
            color: "#fff",
            boxShadow: activeSource === "webcam"
              ? "0 2px 12px rgba(0,204,102,0.35)"
              : "0 2px 12px rgba(0,170,85,0.2)",
          }}
        >
          <span>📷</span>
          <span>Live Feed</span>
        </button>

        {/* Stop */}
        <button
          onClick={handleStop}
          style={{
            border: "none",
            borderRadius: "8px",
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            cursor: "pointer",
            letterSpacing: "0.5px",
            transition: "all 0.25s ease",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "linear-gradient(135deg, #cc2222 0%, #991111 100%)",
            color: "#fff",
            boxShadow: "0 2px 12px rgba(204,34,34,0.2)",
          }}
        >
          <span>⏹</span>
          <span>Stop</span>
        </button>
      </div>

      {/* ── Status Message ── */}
      {status && (
        <div style={{
          marginTop: "10px",
          padding: "8px 12px",
          borderRadius: "6px",
          fontSize: "12px",
          fontWeight: 600,
          background: status.type === "success" ? "#002a1a" : "#2a0000",
          color: status.type === "success" ? "#00ff88" : "#ff4444",
          border: `1px solid ${status.type === "success" ? "#00aa5540" : "#cc222240"}`,
          animation: "fadeIn 0.3s ease",
        }}>
          {status.msg}
        </div>
      )}

      {/* ── Instructions ── */}
      {!activeSource && !uploading && (
        <div style={{
          marginTop: "10px",
          padding: "10px 14px",
          borderRadius: "6px",
          background: "#0a0e1e",
          border: "1px solid #1e2a4a",
          fontSize: "11px",
          color: "#4a5a7a",
          lineHeight: 1.6,
        }}>
          Upload a crowd video file or use live monitoring.
        </div>
      )}
    </div>
  );
}
