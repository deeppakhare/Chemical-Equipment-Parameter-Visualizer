import React from "react";

export default function DataTable({ preview = [] }) {
  if (!preview || preview.length === 0) {
    return <p style={{ color: "var(--muted)" }}>No preview rows available.</p>;
  }
  const cols = Object.keys(preview[0]);

  return (
    <div className="table-scroll" style={{ marginTop: 8 }}>
      <table className="table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.map((row, i) => (
            <tr key={i}>
              {cols.map((c, j) => (
                <td key={j}>{row[c]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
