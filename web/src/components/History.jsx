import React, { useEffect, useState } from "react";
import { getHistoryMock, getSummaryMock } from "../api/mockServer";
import Papa from "papaparse";

/**
 * History component:
 * - loads history (mock or backend)
 * - on Load: fetches summary; if summary.raw_preview is only a small preview,
 *   fetch the full CSV from public/ and parse it (so preview shows all rows).
 */
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
    // publicCsvPath is like "/sample_equipment_data.csv" and will be served from web/public
    const resp = await fetch(publicCsvPath);
    if (!resp.ok) throw new Error(`Failed to fetch CSV: ${resp.status}`);
    const text = await resp.text();
    // parse full CSV to array of objects
    const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
    if (parsed.errors && parsed.errors.length) {
      console.warn("PapaParse errors:", parsed.errors);
    }
    return parsed.data || [];
  }

  async function loadEntry(entry) {
    try {
      // get summary (from backend or fallback public JSON)
      const summaryUrl = entry.summary_url || "/sample_summary_api_payload.json";
      const summary = await getSummaryMock(summaryUrl);

      // If server summary includes only a tiny preview (or no raw_preview), attempt to fetch full CSV
      const expectedRows = summary.rows || 0;
      const currentPreviewCount = (summary.raw_preview && summary.raw_preview.length) || 0;

      // If preview smaller than total rows, try to fetch full CSV (served from web/public/)
      if (expectedRows > 0 && currentPreviewCount < expectedRows) {
        // Attempt to fetch CSV from public. Use the public CSV file name in your project:
        // ensure web/public/sample_equipment_data.csv exists (copied from repo samples)
        try {
          const fullRows = await fetchAndParseCsv("/sample_equipment_data.csv");
          if (fullRows && fullRows.length) {
            summary.raw_preview = fullRows;
          }
        } catch (err) {
          // If fetching CSV fails, leave the smaller preview as-is
          console.warn("Failed to fetch/parse full CSV, keeping preview:", err);
        }
      }

      // Pass the possibly-updated summary back to parent (App)
      onLoadSummary(summary);
    } catch (err) {
      console.error("Failed to load entry summary:", err);
      alert("Failed to load dataset summary. See console for details.");
    }
  }

  return (
    <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
      <h4>History</h4>
      {loading ? <p>Loading…</p> : null}
      {!history || history.length === 0 ? (
        <p>No history.</p>
      ) : (
        <div>
          {history.map((h) => (
            <div key={h.dataset_id} style={{ padding: 8, borderBottom: "1px solid #fafafa" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <strong>{h.dataset_id}</strong>
                  <div style={{ fontSize: 12, color: "#666" }}>{new Date(h.uploaded_at).toLocaleString()}</div>
                </div>
                <div>
                  <button onClick={() => loadEntry(h)} style={{ padding: "6px 8px" }}>
                    Load
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
