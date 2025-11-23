// web/src/App.jsx
import React, { useContext, useState, useMemo } from "react";
import { AuthContext } from "./AuthContext";
import Login from "./components/Login";
import Upload from "./components/Upload";
import DataTable from "./components/DataTable";
import ChartCard from "./components/ChartCard";
import History from "./components/History";
import { downloadDatasetReport } from "./api/reports";
import "./index.css";

export default function App() {
  const { token, logout } = useContext(AuthContext);
  const [summary, setSummary] = useState(null);

  // small derived KPIs for the KPI row
  const kpis = useMemo(() => {
    if (!summary) return { rows: 0, cols: 0, numericCount: 0, lastUpload: null };
    return {
      rows: summary.rows || (summary.raw_preview ? summary.raw_preview.length : 0),
      cols: summary.columns ? summary.columns.length : (summary.raw_preview && summary.raw_preview[0] ? Object.keys(summary.raw_preview[0]).length : 0),
      numericCount: (summary.numeric_columns || []).length,
      lastUpload: summary.uploaded_at || null
    };
  }, [summary]);

  return (
    <div className="app-wrap">
      <header className="header">
        <div className="brand">
          <div className="logo">CE</div>
          <div>
            <div className="title">Chemical Equipment Parameter Visualizer</div>
            <div className="subtitle">Web demo — Upload • Analyze • Report</div>
          </div>
        </div>

        <div className="header-actions">
          {token ? <div className="auth-pill">Authenticated</div> : null}
          {token ? (
            <button className="btn" onClick={logout}>Logout</button>
          ) : null}
        </div>
      </header>

      {!token ? (
        <div style={{ display: "flex", justifyContent: "center", marginTop: 40 }}>
          <div className="card" style={{ width: 420 }}>
            <Login />
          </div>
        </div>
      ) : (
        <div className="content">
          <div>
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0 }}>Upload & Summary</h3>
                <div style={{ color: "var(--muted)", fontSize: 13 }}>Quick demo mode</div>
              </div>

              <div style={{ marginTop: 12 }}>
                <Upload onSummary={(s) => setSummary(s)} />
              </div>
            </div>

            <div className="card" style={{ marginTop: 12 }}>
              <div className="kpi-row">
                <div className="kpi">
                  <div className="kpi-value">{kpis.rows}</div>
                  <div className="kpi-label">Rows</div>
                </div>
                <div className="kpi">
                  <div className="kpi-value">{kpis.cols}</div>
                  <div className="kpi-label">Columns</div>
                </div>
                <div className="kpi">
                  <div className="kpi-value">{kpis.numericCount}</div>
                  <div className="kpi-label">Numeric columns</div>
                </div>
                <div className="kpi">
                  <div className="kpi-value">{kpis.lastUpload ? new Date(kpis.lastUpload).toLocaleString() : "-"}</div>
                  <div className="kpi-label">Last upload</div>
                </div>
              </div>

              <div style={{ marginTop: 8 }}>
                <h4 style={{ margin: "8px 0" }}>Data Preview / Summary</h4>
                {summary ? (
                  <>
                    <DataTable preview={summary.raw_preview || []} />
                    <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
                      <ChartCard summary={summary} />
                    </div>
                  </>
                ) : (
                  <p style={{ color: "var(--muted)" }}>No dataset loaded. Upload a CSV to see preview & charts.</p>
                )}
              </div>
            </div>
          </div>

          <aside>
            <div className="card aside-section">
              <h4 style={{ margin: 0 }}>History</h4>
              <History onLoadSummary={(s) => setSummary(s)} />
            </div>

            <div className="card aside-section" style={{ marginTop: 12 }}>
              <h4 style={{ margin: 0 }}>Actions</h4>
              <div className="actions">
                <button
                  className="btn"
                  onClick={async () => {
                    if (!summary) return alert("Load a dataset first");
                    const candidate = summary.id || summary.dataset_id || summary.original_filename;
                    try {
                      await downloadDatasetReport(candidate);
                      alert("Report download started (check browser downloads).");
                    } catch (err) {
                      console.error(err);
                      alert("Failed to download report: " + (err.message || err));
                    }
                  }}
                >
                  Generate / Download Report
                </button>

                <button
                  className="btn secondary"
                  onClick={() => {
                    setSummary(null);
                    localStorage.removeItem("last_summary");
                  }}
                >
                  Clear
                </button>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
