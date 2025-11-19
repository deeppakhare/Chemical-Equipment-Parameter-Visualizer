import React, { useEffect, useState } from "react";
import { getHistoryMock, getSummaryMock } from "../api/mockServer";

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

  async function loadEntry(entry) {
    const summary = await getSummaryMock("/sample_summary_api_payload.json");
    onLoadSummary(summary);
  }

  return (
    <div style={{border:"1px solid #eee", padding:12, borderRadius:8}}>
      <h4>History</h4>
      {loading ? <p>Loading…</p> : null}
      {!history || history.length === 0 ? <p>No history.</p> : (
        <div>
          {history.map((h) => (
            <div key={h.dataset_id} style={{padding:8, borderBottom:"1px solid #fafafa"}}>
              <div style={{display:"flex", justifyContent:"space-between"}}>
                <div>
                  <strong>{h.dataset_id}</strong>
                  <div style={{fontSize:12, color:"#666"}}>{new Date(h.uploaded_at).toLocaleString()}</div>
                </div>
                <div>
                  <button onClick={() => loadEntry(h)} style={{padding:"6px 8px"}}>Load</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
