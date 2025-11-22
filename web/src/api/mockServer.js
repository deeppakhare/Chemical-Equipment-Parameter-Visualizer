// web/src/api/mockServer.js
import client from "./client";

/**
 * Helper: check if Authorization header is present
 */
function hasAuth() {
  return !!client.defaults.headers.common["Authorization"];
}

/**
 * loginMock not needed because you have real login; keep for completeness
 */
export async function loginMock(username, password) {
  // If backend is configured, use real token endpoint
  try {
    const res = await client.post("/api-token-auth/", { username, password });
    return { token: res.data.token };
  } catch  {
    // fallback fake token for offline dev
    await new Promise((r) => setTimeout(r, 300));
    return { token: "fake-token-offline" };
  }
}

/**
 * uploadMock: if token & backend available -> post to backend
 * otherwise return static sample pointing to public/sample_summary_api_payload.json
 */
export async function uploadMock(file) {
  // If auth token present, try real upload
  if (hasAuth()) {
    try {
      const fd = new FormData();
      // 'file' may be a File object (from input) or a path string in dev tests
      if (file instanceof File) {
        fd.append("file", file);
      } else {
        // in dev, callers may pass a path string (not for browser),
        // so we'll still fall back to static response
      }
      const res = await client.post("/api/datasets/upload/", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      return res.data;
    } catch (err) {
      console.warn("Backend upload failed, falling back to mock", err);
    }
  }

  // fallback mock response (served from web/public/)
  await new Promise((r) => setTimeout(r, 600));
  return {
    dataset_id: "sample_equipment_data.csv",
    summary_url: "/sample_summary_api_payload.json",
    history_url: "/api/datasets/history/"
  };
}

/**
 * getSummaryMock: accepts datasetId or summary_url; fetches from backend if token present, else from public static JSON
 */
// robust version of getSummaryMock
export async function getSummaryMock(datasetIdOrUrl) {
  // pick a URL: prefer explicit URL, else public sample
  const publicUrl = "/sample_summary_api_payload.json";
  const inferredUrl = (typeof datasetIdOrUrl === "string" && datasetIdOrUrl.startsWith("/"))
    ? datasetIdOrUrl
    : publicUrl;

  // If authenticated, try backend endpoints first
  if (hasAuth()) {
    // If datasetIdOrUrl looks like a numeric id, call backend summary endpoint
    if (/^\d+$/.test(String(datasetIdOrUrl))) {
      try {
        const res = await client.get(`/api/datasets/${datasetIdOrUrl}/summary/`);
        return res.data;
      } catch (err) {
        console.warn("Backend summary fetch failed:", err);
        // fall through to try public JSON
      }
    } else {
      // If it's a path like "/sample_summary_api_payload.json", try backend (use client)
      try {
        const res = await client.get(inferredUrl);
        return res.data;
      } catch (err) {
        console.warn("Backend direct summary fetch failed, falling back to public", err);
      }
    }
  }

  // Fallback: fetch the static file from Vite public/
  const resp = await fetch(publicUrl, { cache: "no-store" });
  if (!resp.ok) {
    throw new Error(`Could not load sample summary JSON from ${publicUrl} (status ${resp.status})`);
  }
  // Try parse JSON safely
  const contentType = resp.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    // got HTML (likely a 404 page) — raise informative error
    const text = await resp.text();
    console.warn("Expected JSON but got:", text.slice(0, 200));
    throw new Error("Sample summary fetch returned non-JSON (likely 404).");
  }
  return await resp.json();
}

/**
 * getHistoryMock: uses backend if token exists, otherwise returns simple mock
 */
export async function getHistoryMock() {
  if (hasAuth()) {
    try {
      const res = await client.get("/api/datasets/history/");
      return res.data;
    } catch (err) {
      console.warn("Backend history fetch failed, falling back to mock", err);
    }
  }

  await new Promise((r) => setTimeout(r, 200));
  return [
    {
      dataset_id: "sample_equipment_data.csv",
      uploaded_at: new Date().toISOString(),
      rows: 15,
      columns: ["ID", "Flowrate", "Pressure", "Temperature", "Note"]
    }
  ];
}
