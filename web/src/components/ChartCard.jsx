import React, { useState, useMemo } from "react";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  CategoryScale,
  Tooltip,
  Legend
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip, Legend);

export default function ChartCard({ summary }) {
  const numeric = useMemo(() => summary?.numeric_columns || [], [summary]);
  const preview = useMemo(() => summary?.raw_preview || [], [summary]);

  const [yCol, setYCol] = useState(numeric[0] || null);

  React.useEffect(() => {
    if (numeric.length) setYCol(numeric[0]);
  }, [numeric]);

  const labels = useMemo(() => {
    if (preview.length) return preview.map((_, idx) => idx + 1);
    const count = summary?.rows || 10;
    return Array.from({ length: count }, (_, i) => i + 1);
  }, [preview, summary]);

  const data = useMemo(() => {
    if (!yCol) return { labels: [], datasets: [] };

    const values = preview.length
      ? preview.map((row) => Number(row[yCol] ?? NaN))
      : Array.from({ length: summary?.rows || 10 }, () => summary?.summary?.[yCol]?.mean ?? 0);

    return {
      labels,
      datasets: [
        {
          label: yCol,
          data: values,
          fill: false,
          tension: 0.2,
          borderColor: "#2563eb",
          pointRadius: 3
        }
      ]
    };
  }, [yCol, preview, labels, summary]);

  if (!numeric.length) return <p style={{ color: "var(--muted)" }}>No numeric columns available.</p>;
  if (!yCol) return null;

  // compute quick stats
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const stats = useMemo(() => {
    const s = summary?.summary || {};
    const colStats = s[yCol] || {};
    return {
      mean: colStats.mean ?? (preview.length ? (preview.reduce((a,b)=>a+Number(b[yCol]||0),0)/preview.length) : 0),
      min: colStats.min ?? Math.min(...(preview.map(r=>Number(r[yCol]||0)) || [0])),
      max: colStats.max ?? Math.max(...(preview.map(r=>Number(r[yCol]||0)) || [0]))
    };
  }, [summary, preview, yCol]);

  return (
    <div className="chart-wrap card" style={{ padding: 12 }}>
      <div className="chart-toolbar">
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <h4 style={{ margin: 0 }}>Chart — {yCol}</h4>
          <select value={yCol} onChange={(e) => setYCol(e.target.value)}>
            {numeric.map((col) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </div>
        <div className="stat-badges">
          <div className="badge">mean: {Number(stats.mean).toFixed(2)}</div>
          <div className="badge" style={{ background: "rgba(14,165,233,0.12)", color:"#0369a1" }}>min: {Number(stats.min).toFixed(2)}</div>
          <div className="badge" style={{ background: "rgba(239,68,68,0.08)", color:"#b91c1c" }}>max: {Number(stats.max).toFixed(2)}</div>
        </div>
      </div>

      <div style={{ height: 260 }}>
        <Line data={data} />
      </div>

      <div style={{ marginTop: 8 }}>
        <small style={{ color: "var(--muted)" }}>Tip: choose another column to view trend for different parameters.</small>
      </div>
    </div>
  );
}
