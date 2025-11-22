// web/src/App.jsx
import React, { useContext, useState } from "react";
import { AuthContext } from "./AuthContext";
import Login from "./components/Login";
import Upload from "./components/Upload";
import DataTable from "./components/DataTable";
import ChartCard from "./components/ChartCard";
import History from "./components/History";

export default function App() {
  const { token, logout } = useContext(AuthContext);
  const [summary, setSummary] = useState(null);

  return (
    <div style={{ padding: 20, fontFamily: "Inter, Arial, sans-serif" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <h2>Chemical Equipment Parameter Visualizer — Web (Demo)</h2>
        {token ? (
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ fontSize: 13, color: "#444", alignSelf: "center" }}>
              Authenticated
            </div>
            <button onClick={logout}>Logout</button>
          </div>
        ) : null}
      </header>

      {!token ? (
        <Login />
      ) : (
        <main
          style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: 16 }}
        >
          <section>
            <Upload onSummary={(s) => setSummary(s)} />
            <div style={{ marginTop: 16 }}>
              <h3>Data Preview / Summary</h3>
              {summary ? (
                <>
                  <DataTable preview={summary.raw_preview || []} />
                  <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
                    <ChartCard summary={summary} />
                  </div>
                </>
              ) : (
                <p>No dataset loaded. Upload a CSV to see preview & charts.</p>
              )}
            </div>
          </section>

          <aside>
            <History onLoadSummary={(s) => setSummary(s)} />
            <div style={{ marginTop: 16 }}>
              <h4>Actions</h4>
              <button
                onClick={() => {
                  if (!summary) return alert("Load a dataset first");
                  // Mock "generate report" - download a sample PDF stored in public/
                  const a = document.createElement("a");
                  a.href = "/sample_report.pdf";
                  a.download = `${summary.dataset_id || "report"}.pdf`;
                  a.click();
                }}
              >
                Generate / Download Report (mock)
              </button>
            </div>
          </aside>
        </main>
      )}
    </div>
  );
}
