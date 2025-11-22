// web/src/components/Upload.jsx
import React, { useState } from "react";
import { uploadMock, getSummaryMock } from "../api/mockServer";
import Papa from "papaparse";
import client from "../api/client";

/**
 * Upload component:
 * - Shows small client-side preview (previewRows)
 * - When uploading:
 *    - if Authorization token is present in axios client, call real backend via uploadFile()
 *    - otherwise call uploadMock()
 * - After upload, parse the full selected CSV file client-side and attach full rows
 *   to summary.raw_preview so the UI immediately shows the whole file.
 */

export default function Upload({ onSummary }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [previewRows, setPreviewRows] = useState(null);

  function onFileChange(e) {
    const f = e.target.files[0];
    setFile(f);
    if (f) {
      // quick client-side preview using PapaParse (first 10 rows)
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

  // use the real backend upload via axios client
  async function uploadFileToBackend(fileObj) {
    const fd = new FormData();
    fd.append("file", fileObj);
    const resp = await client.post("/api/datasets/upload/", fd, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    return resp.data; // { dataset_id, summary_url, history_url }
  }

  // helper: parse full CSV file (File object) into array of row objects
  function parseFullCsvFile(fileObj) {
    return new Promise((resolve, reject) => {
      Papa.parse(fileObj, {
        header: true,
        skipEmptyLines: true,
        worker: false,
        complete: (results) => resolve(results.data || []),
        error: (err) => reject(err)
      });
    });
  }

  async function doUpload() {
    if (!file) return alert("Choose a CSV file first");
    setLoading(true);
    try {
      // choose real upload when an Authorization header (Token) is set on client
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

      // get summary (either via summary_url returned by backend or fallback)
      const summary = await getSummaryMock(uploadResp.summary_url || uploadResp.dataset_id);

      // If the user selected a local file, parse the full CSV client-side and attach full rows
      // This ensures DataTable shows the full CSV immediately after upload
      if (file instanceof File) {
        try {
          const fullRows = await parseFullCsvFile(file);
          if (fullRows && fullRows.length) {
            summary.raw_preview = fullRows;
            // update summary.rows if missing or smaller
            summary.rows = Math.max(summary.rows || 0, fullRows.length);
            // recompute numeric_columns if missing
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

      // finally pass summary to parent
      onSummary(summary);
    } catch (err) {
      console.error(err);
      alert("Upload failed (mock or backend). See console for details.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ border: "1px solid #e2e8f0", padding: 12, borderRadius: 8 }}>
      <h3>Upload CSV (mock)</h3>
      <input type="file" accept=".csv" onChange={onFileChange} />
      <div style={{ marginTop: 8 }}>
        <button onClick={doUpload} disabled={loading} style={{ padding: "8px 12px" }}>
          {loading ? "Uploading…" : "Upload CSV"}
        </button>
      </div>

      {previewRows && (
        <div style={{ marginTop: 12 }}>
          <h4>Preview (first {previewRows.length} rows)</h4>
          <div style={{ maxHeight: 160, overflow: "auto", border: "1px solid #f0f0f0" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {Object.keys(previewRows[0] || {}).map((c) => (
                    <th key={c} style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #eee" }}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((r, i) => (
                  <tr key={i}>
                    {Object.values(r).map((v, j) => (
                      <td key={j} style={{ padding: 6, borderBottom: "1px solid #fafafa" }}>
                        {v}
                      </td>
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
