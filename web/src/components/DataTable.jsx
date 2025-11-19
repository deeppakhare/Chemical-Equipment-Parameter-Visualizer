import React from "react";

export default function DataTable({ preview = [] }) {
  if (!preview || preview.length === 0) {
    return <p>No preview rows available.</p>;
  }
  const cols = Object.keys(preview[0]);

  return (
    <div style={{border:"1px solid #eee", padding:8, borderRadius:8}}>
      <table style={{width:"100%", borderCollapse:"collapse"}}>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c} style={{textAlign:"left", padding:6, borderBottom:"1px solid #eee"}}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.map((row, i) => (
            <tr key={i}>
              {cols.map((c, j) => (
                <td key={j} style={{padding:6, borderBottom:"1px solid #fafafa"}}>{row[c]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
