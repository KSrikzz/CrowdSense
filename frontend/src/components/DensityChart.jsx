export default function DensityChart({ densityLog = [] }) {
  const width = 760;
  const height = 220;
  const pad = 28;

  const liveData = densityLog.slice(-40);
  const hasEnough = liveData.length >= 2;

  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

  const makeForecast = (points) => {
    if (points.length < 4) return [];

    const recent = points.slice(-8);
    const n = recent.length;

    const xs = recent.map((_, i) => i);
    const ys = recent.map((p) => Number(p.v || 0));

    const xMean = xs.reduce((a, b) => a + b, 0) / n;
    const yMean = ys.reduce((a, b) => a + b, 0) / n;

    let num = 0;
    let den = 0;
    for (let i = 0; i < n; i++) {
      num += (xs[i] - xMean) * (ys[i] - yMean);
      den += (xs[i] - xMean) ** 2;
    }

    const slope = den === 0 ? 0 : num / den;
    const forecast = [];
    const lastT = Number(points[points.length - 1]?.t ?? points.length);

    for (let i = 1; i <= 5; i++) {
      const raw = yMean + slope * ((n - 1 + i) - xMean);
      forecast.push({
        t: lastT + i,
        v: Math.round(clamp(raw, 0, 999)),
      });
    }

    return forecast;
  };

  const forecastData = makeForecast(liveData);
  const allData = [...liveData, ...forecastData];
  const maxVal = Math.max(10, ...allData.map((d) => Number(d.v || 0)));
  const chartW = width - pad * 2;
  const chartH = height - pad * 2;

  const xFor = (i, total) => {
    if (total <= 1) return pad;
    return pad + (i / (total - 1)) * chartW;
  };

  const yFor = (v) => pad + chartH - (Number(v || 0) / maxVal) * chartH;

  const solidPath = liveData
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i, allData.length)} ${yFor(p.v)}`)
    .join(" ");

  const forecastPath =
    forecastData.length > 0
      ? forecastData
          .map((p, i) => {
            const idx = liveData.length - 1 + i;
            return `${i === 0 ? "M" : "L"} ${xFor(idx, allData.length)} ${yFor(i === 0 ? liveData[liveData.length - 1]?.v : p.v)}`;
          })
          .join(" ")
      : "";

  const areaPath =
    liveData.length > 1
      ? `
        M ${xFor(0, allData.length)} ${height - pad}
        ${liveData
          .map((p, i) => `L ${xFor(i, allData.length)} ${yFor(p.v)}`)
          .join(" ")}
        L ${xFor(liveData.length - 1, allData.length)} ${height - pad}
        Z
      `
      : "";

  const latest = liveData[liveData.length - 1]?.v ?? 0;
  const trend =
    liveData.length >= 2
      ? latest > liveData[liveData.length - 2].v
        ? "Rising"
        : latest < liveData[liveData.length - 2].v
        ? "Falling"
        : "Stable"
      : "Stable";

  return (
    <div
      style={{
        background: "#0f1629",
        border: "1px solid #1e2a4a",
        borderRadius: "10px",
        padding: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "12px",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ fontSize: "12px", color: "#5577aa", fontWeight: 700 }}>
          📈 CROWD DENSITY TREND
        </div>

        <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "#7f93c9" }}>
          <span>Now: <strong style={{ color: "#00dcff" }}>{latest}</strong></span>
          <span>Trend: <strong style={{ color: trend === "Rising" ? "#ff8800" : trend === "Falling" ? "#ff4444" : "#00ff88" }}>{trend}</strong></span>
          <span>Forecast: <strong style={{ color: "#a78bfa" }}>Next 5 frames</strong></span>
        </div>
      </div>

      <div
        style={{
          background: "#0a0e1e",
          border: "1px solid #18233f",
          borderRadius: "8px",
          padding: "8px",
        }}
      >
        {!hasEnough ? (
          <div
            style={{
              height: `${height}px`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#5577aa",
              fontSize: "13px",
            }}
          >
            Waiting for live crowd data...
          </div>
        ) : (
          <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ display: "block" }}>
            <defs>
              <linearGradient id="densityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00dcff" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#00dcff" stopOpacity="0.02" />
              </linearGradient>
            </defs>

            {[0, 0.25, 0.5, 0.75, 1].map((g, i) => {
              const y = pad + chartH * g;
              return (
                <g key={i}>
                  <line
                    x1={pad}
                    y1={y}
                    x2={width - pad}
                    y2={y}
                    stroke="#1e2a4a"
                    strokeWidth="1"
                  />
                  <text
                    x={6}
                    y={y + 4}
                    fill="#5577aa"
                    fontSize="10"
                    fontFamily="monospace"
                  >
                    {Math.round(maxVal * (1 - g))}
                  </text>
                </g>
              );
            })}

            {Array.from({ length: Math.min(allData.length, 8) }).map((_, i) => {
              const x = pad + (i / Math.max(1, 7)) * chartW;
              return (
                <line
                  key={i}
                  x1={x}
                  y1={pad}
                  x2={x}
                  y2={height - pad}
                  stroke="#14203a"
                  strokeWidth="1"
                />
              );
            })}

            {areaPath && <path d={areaPath} fill="url(#densityFill)" />}

            <path
              d={solidPath}
              fill="none"
              stroke="#00dcff"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {forecastPath && (
              <path
                d={forecastPath}
                fill="none"
                stroke="#a78bfa"
                strokeWidth="3"
                strokeDasharray="7 6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {liveData.map((p, i) => (
              <circle
                key={`live-${i}`}
                cx={xFor(i, allData.length)}
                cy={yFor(p.v)}
                r="3.5"
                fill="#00dcff"
              />
            ))}

            {forecastData.map((p, i) => {
              const idx = liveData.length + i;
              return (
                <circle
                  key={`forecast-${i}`}
                  cx={xFor(idx, allData.length)}
                  cy={yFor(p.v)}
                  r="3.5"
                  fill="#a78bfa"
                />
              );
            })}

            <line
              x1={pad}
              y1={height - pad}
              x2={width - pad}
              y2={height - pad}
              stroke="#2b3b63"
              strokeWidth="1.5"
            />
          </svg>
        )}
      </div>

      <div
        style={{
          marginTop: "10px",
          display: "flex",
          gap: "14px",
          flexWrap: "wrap",
          fontSize: "11px",
          color: "#6c82b8",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#00dcff", display: "inline-block" }} />
          Live count
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "16px", height: "0", borderTop: "3px dashed #a78bfa", display: "inline-block" }} />
          Forecast line
        </span>
      </div>
    </div>
  );
}