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
  // memoized derived values
  const numeric = useMemo(() => summary?.numeric_columns || [], [summary]);
  const preview = useMemo(() => summary?.raw_preview || [], [summary]);

  // pick yCol directly, without useEffect
  const defaultY = numeric.length ? numeric[0] : null;
  const [yCol, setYCol] = useState(defaultY);

  // when summary changes, reset yCol safely
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
          tension: 0.2
        }
      ]
    };
  }, [yCol, preview, labels, summary]);

  if (!numeric.length) return <p>No numeric columns available.</p>;
  if (!yCol) return null;

  return (
    <div style={{ border: "1px solid #e6eef8", padding: 12, borderRadius: 8, width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h4 style={{ margin: 0 }}>Chart — {yCol}</h4>
        <select value={yCol} onChange={(e) => setYCol(e.target.value)}>
          {numeric.map((col) => (
            <option key={col} value={col}>
              {col}
            </option>
          ))}
        </select>
      </div>
      <div style={{ height: 260 }}>
        <Line data={data} />
      </div>
      <div style={{ marginTop: 8 }}>
        <small>Pick different columns from dropdown.</small>
      </div>
    </div>
  );
}
