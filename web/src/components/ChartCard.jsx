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
  const numeric = summary?.numeric_columns || [];
  const preview = summary?.raw_preview || [];

  const [yCol, setYCol] = useState(numeric[0] || null);
  const labels = useMemo(() => (preview.length ? preview.map((r, i) => i + 1) : Array.from({length: summary?.rows || 10}, (_,i) => i+1)), [preview, summary]);

  const data = useMemo(() => {
    const values = preview.length ? preview.map((r) => Number(r[yCol] ?? NaN)) : Array.from({length: summary?.rows || 10}, () => summary?.summary?.[yCol]?.mean ?? 0);
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

  if (!yCol) return <p>No numeric columns available to chart.</p>;

  return (
    <div style={{border:"1px solid #e6eef8", padding:12, borderRadius:8, width: "100%"}}>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <h4 style={{margin:0}}>Chart — {yCol}</h4>
        <select value={yCol} onChange={(e) => setYCol(e.target.value)}>
          {numeric.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </div>
      <div style={{height:260}}>
        <Line data={data} />
      </div>

      <div style={{marginTop:8}}>
        <small>Tip: pick different numeric columns from dropdown.</small>
      </div>
    </div>
  );
}
