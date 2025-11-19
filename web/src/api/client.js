import axios from "axios";

const client = axios.create({
  baseURL: "/", // default to same origin while using public/ mocks; change to backend URL later
  timeout: 15000,
});

export default client;
