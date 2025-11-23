// web/src/components/Upload.jsx
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
      Papa.parse(f, {
        header: true,
        preview: 10,
        skipEmptyLines: true,
        complete: (results) => {
          setPreviewRows(results.data || []);
        }
      });
    } else {
      setPreviewRows(null);
    }
  }

  async function uploadFileToBackend(fileObj) {
    const fd = new FormData();
    fd.append("file", fileObj);
    const resp = await client.post("/api/datasets/upload/", fd, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    return resp.data;
  }

  function parseFullCsvFile(fileObj) {
    return new Promise((resolve, reject) => {
      Papa.parse(fileObj, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => resolve(results.data || []),
        error: (err) => reject(err)
      });
    });
  }

  async function doUpload() {
    if (!file) return alert("Choose a CSV file first");
    setLoading(true);
    try {
      const hasAuth = !!client.defaults.headers.common["Authorization"];
      let uploadResp;
      if (hasAuth) {
        try {
          uploadResp = await uploadFileToBackend(file);
        } catch (err) {
          console.warn("Backend upload failed, falling back to mock", err);
          uploadResp = await uploadMock(file);
        }
      } else {
        uploadResp = await uploadMock(file);
      }

      const summary = await getSummaryMock(uploadResp.summary_url || uploadResp.dataset_id);

      if (file instanceof File) {
        try {
          const fullRows = await parseFullCsvFile(file);
          if (fullRows && fullRows.length) {
            summary.raw_preview = fullRows;
            summary.rows = Math.max(summary.rows || 0, fullRows.length);
            if (!summary.numeric_columns || summary.numeric_columns.length === 0) {
              const sampleRow = fullRows[0] || {};
              const numericCols = Object.keys(sampleRow).filter((k) => {
                const v = sampleRow[k];
                return v !== null && v !== "" && !isNaN(Number(v));
              });
              summary.numeric_columns = numericCols;
            }
          }
        } catch (err) {
          console.warn("Failed to parse full CSV client-side:", err);
        }
      }

      onSummary(summary);
    } catch (err) {
      console.error(err);
      alert("Upload failed (mock or backend). See console for details.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="upload-area">
        <div className="upload-left">
          <div style={{ fontWeight: 700 }}>Upload CSV</div>
          <div className="u-meta">Supported: comma-separated CSV with header row</div>
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <input type="file" accept=".csv" onChange={onFileChange} />
            <button className="btn small" onClick={doUpload} disabled={loading}>
              {loading ? "Uploading…" : "Upload"}
            </button>
            <button
              className="btn secondary small"
              onClick={() => {
                setFile(null);
                setPreviewRows(null);
              }}
            >
              Clear
            </button>
          </div>
        </div>
        <div style={{ width: 160, textAlign: "right" }}>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>Selected</div>
          <div style={{ fontWeight: 700 }}>{file ? file.name : "No file"}</div>
        </div>
      </div>

      {previewRows && (
        <div className="preview-wrap">
          <h4 style={{ marginTop: 12 }}>Preview (first {previewRows.length} rows)</h4>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  {Object.keys(previewRows[0] || {}).map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((r, i) => (
                  <tr key={i}>
                    {Object.values(r).map((v, j) => (
                      <td key={j}>{v}</td>
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
