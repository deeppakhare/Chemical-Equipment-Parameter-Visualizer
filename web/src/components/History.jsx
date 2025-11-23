import React, { useEffect, useState } from "react";
import { getHistoryMock, getSummaryMock } from "../api/mockServer";
import Papa from "papaparse";

export default function History({ onLoadSummary }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const h = await getHistoryMock();
      setHistory(h);
      setLoading(false);
    }
    load();
  }, []);

  async function fetchAndParseCsv(publicCsvPath) {
    const resp = await fetch(publicCsvPath);
    if (!resp.ok) throw new Error(`Failed to fetch CSV: ${resp.status}`);
    const text = await resp.text();
    const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
    if (parsed.errors && parsed.errors.length) {
      console.warn("PapaParse errors:", parsed.errors);
    }
    return parsed.data || [];
  }

  async function loadEntry(entry) {
    try {
      const summaryUrl = entry.summary_url || "/sample_summary_api_payload.json";
      const summary = await getSummaryMock(summaryUrl);

      const expectedRows = summary.rows || 0;
      const currentPreviewCount = (summary.raw_preview && summary.raw_preview.length) || 0;

      if (expectedRows > 0 && currentPreviewCount < expectedRows) {
        try {
          const fullRows = await fetchAndParseCsv("/sample_equipment_data.csv");
          if (fullRows && fullRows.length) {
            summary.raw_preview = fullRows;
          }
        } catch (err) {
          console.warn("Failed to fetch/parse full CSV, keeping preview:", err);
        }
      }

      onLoadSummary(summary);
    } catch (err) {
      console.error("Failed to load entry summary:", err);
      alert("Failed to load dataset summary. See console for details.");
    }
  }

  return (
    <div>
      {loading ? <p>Loading…</p> : null}
      {!history || history.length === 0 ? (
        <p>No history.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {history.map((h) => (
            <div key={h.dataset_id} className="history-item">
              <div style={{ display: "flex", flexDirection: "column" }}>
                <strong>{h.original_filename || h.dataset_id}</strong>
                <div className="history-meta">{h.rows} rows • {h.columns ? h.columns.join(", ") : ""}</div>
                <div className="history-meta" style={{ marginTop: 6 }}>
                  {h.uploaded_at ? new Date(h.uploaded_at).toLocaleString() : ""}
                </div>
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn small" onClick={() => loadEntry(h)}>Load</button>
                <a className="btn small secondary" href={h.file || "#"} target="_blank" rel="noreferrer">Open CSV</a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
