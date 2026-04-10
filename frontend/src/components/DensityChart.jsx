import { useEffect, useRef } from "react";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement,
  LineElement, Filler, Tooltip, Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

export default function DensityChart({ densityLog }) {
  const labels = densityLog.map(d => d.t);
  const values = densityLog.map(d => d.v);

  const data = {
    labels,
    datasets: [{
      label: "Total People Detected",
      data: values,
      borderColor: "#00dcff",
      backgroundColor: "rgba(0,220,255,0.08)",
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      borderWidth: 2,
    }],
  };

  const options = {
    responsive: true,
    animation: { duration: 150 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#0f1629",
        borderColor: "#1e2a4a",
        borderWidth: 1,
        titleColor: "#00dcff",
        bodyColor: "#aabbcc",
      },
    },
    scales: {
      x: {
        display: false,
      },
      y: {
        min: 0,
        grid:  { color:"#1e2a4a" },
        ticks: { color:"#5577aa", font:{ size:11 } },
      },
    },
  };

  return (
    <div style={{ background:"#0f1629", border:"1px solid #1e2a4a",
                  borderRadius:"10px", padding:"12px" }}>
      <div style={{ fontSize:"12px", color:"#5577aa", marginBottom:"8px",
                    display:"flex", justifyContent:"space-between" }}>
        <span>📈 Live Crowd Density Trend</span>
        <span style={{ color:"#00dcff" }}>last 60 frames</span>
      </div>
      <Line data={data} options={options} height={80} />
    </div>
  );
}
