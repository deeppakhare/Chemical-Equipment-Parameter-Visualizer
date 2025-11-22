import React, { useState } from "react";
import { uploadMock, getSummaryMock } from "../api/mockServer";
import Papa from "papaparse";
import client from "../api/client";

export default function Upload({ onSummary }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [previewRows, setPreviewRows] = useState(null);

  function onFileChange(e) {
    const f = e.target.files[0];
    setFile(f);
    if (f) {
      // quick client-side preview using PapaParse
      Papa.parse(f, {
        header: true,
        preview: 10,
        complete: (results) => {
          setPreviewRows(results.data);
        }
      });
    } else {
      setPreviewRows(null);
    }
  }

  async function doUpload() {
    if (!file) return alert("Choose a CSV file first");
    setLoading(true);
    try {
      const res = await uploadMock(file);
      const summary = await getSummaryMock(res.summary_url || res.dataset_id);
      // if client-side preview exists, attach it
      if (previewRows) summary.raw_preview = previewRows;
      onSummary(summary);
    } catch (err) {
      console.error(err);
      alert("Upload failed (mock)");
    } finally {
      setLoading(false);
    }
  }

  async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const resp = await client.post("/api/datasets/upload/", fd, { headers: { "Content-Type": "multipart/form-data" }});
  return resp.data; // { dataset_id, summary_url, history_url }
}

  return (
    <div style={{border:"1px solid #e2e8f0", padding:12, borderRadius:8}}>
      <h3>Upload CSV (mock)</h3>
      <input type="file" accept=".csv" onChange={onFileChange} />
      <div style={{marginTop:8}}>
        <button onClick={doUpload} disabled={loading} style={{padding:"8px 12px"}}>
          {loading ? "Uploading…" : "Upload CSV"}
        </button>
      </div>

      {previewRows && (
        <div style={{marginTop:12}}>
          <h4>Preview (first {previewRows.length} rows)</h4>
          <div style={{maxHeight:160, overflow:"auto", border:"1px solid #f0f0f0"}}>
            <table style={{width:"100%", borderCollapse:"collapse"}}>
              <thead>
                <tr>
                  {Object.keys(previewRows[0] || {}).map((c) => (
                    <th key={c} style={{textAlign:"left", padding:6, borderBottom:"1px solid #eee"}}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((r, i) => (
                  <tr key={i}>
                    {Object.values(r).map((v, j) => (
                      <td key={j} style={{padding:6, borderBottom:"1px solid #fafafa"}}>{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
