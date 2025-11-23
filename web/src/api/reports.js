// web/src/api/reports.js
import client from "./client";

/**
 * Download dataset report.
 * Accepts either:
 *  - numeric id (23)
 *  - string id-like (e.g. "23")
 *  - filename (e.g. "sample_equipment_data.csv")
 *
 * If passed a non-numeric string, we query the backend history
 * to find the numeric id that matches original_filename or dataset_id.
 */
async function resolveDatasetId(maybeIdOrName) {
  // if already numeric (or numeric string), return as-is
  if (typeof maybeIdOrName === "number") return maybeIdOrName;
  if (typeof maybeIdOrName === "string" && /^\d+$/.test(maybeIdOrName)) {
    return Number(maybeIdOrName);
  }

  // otherwise fetch history and try to match
  try {
    const res = await client.get("/api/datasets/history/");
    const items = res.data || [];
    // try several fields
    const name = String(maybeIdOrName);
    // match original_filename, dataset_id (string), or file URL ending in name
    const found = items.find((it) => {
      if (!it) return false;
      if (it.id && String(it.id) === name) return true;
      if (it.original_filename && it.original_filename === name) return true;
      if (it.dataset_id && String(it.dataset_id) === name) return true;
      if (it.file && it.file.endsWith(name)) return true;
      return false;
    });
    if (found) return found.id;
    throw new Error("Could not resolve dataset id for: " + maybeIdOrName);
  } catch (err) {
    throw new Error("Failed to resolve dataset id: " + (err.message || err));
  }
}

export async function downloadDatasetReport(datasetIdOrName) {
  const id = await resolveDatasetId(datasetIdOrName);
  // now request PDF by numeric id
  const resp = await client.get(`/api/datasets/${id}/report/`, {
    responseType: "blob",
    timeout: 60000
  });

  const blob = new Blob([resp.data], { type: "application/pdf" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `dataset_report_${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
