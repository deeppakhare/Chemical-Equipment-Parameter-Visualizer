// src/api/mockServer.js
import client from "./client";

// simple fetch wrapper to load the sample JSON from public/
export async function loginMock(username, password) {
  // fake delay
  await new Promise((r) => setTimeout(r, 400));
  return { token: "fake-token-demo" };
}

export async function uploadMock(file) {
  // simulate upload latency
  await new Promise((r) => setTimeout(r, 600));
  // return dataset id and summary_url (we will use static summary in public/)
  return {
    dataset_id: "sample_equipment_data.csv",
    summary_url: "/sample_summary_api_payload.json",
    history_url: "/api/datasets/history/"
  };
}

export async function getSummaryMock(datasetIdOrUrl) {
  // if a URL path is supplied (e.g. /sample_summary_api_payload.json), fetch it
  const url = datasetIdOrUrl && datasetIdOrUrl.startsWith("/") ? datasetIdOrUrl : "/sample_summary_api_payload.json";
  const res = await client.get(url);
  return res.data;
}

export async function getHistoryMock() {
  await new Promise((r) => setTimeout(r, 300));
  // simple history array referencing the sample dataset
  return [
    {
      dataset_id: "sample_equipment_data.csv",
      uploaded_at: new Date().toISOString(),
      rows: 15,
      columns: ["ID","Flowrate","Pressure","Temperature","Note"]
    }
  ];
}
