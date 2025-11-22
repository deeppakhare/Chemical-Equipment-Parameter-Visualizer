import axios from "axios";

const client = axios.create({
  baseURL: "http://localhost:8000", // default to same origin while using public/ mocks; change to backend URL later
  timeout: 15000,
});

// helper to set token globally
export function setAuthToken(token) {
  if (token) client.defaults.headers.common["Authorization"] = `Token ${token}`;
  else delete client.defaults.headers.common["Authorization"];
}

export default client;
