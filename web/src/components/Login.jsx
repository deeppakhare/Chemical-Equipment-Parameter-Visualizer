import React, { useState, useContext } from "react";
import client from "../api/client";
import { AuthContext } from "../AuthContext";

export default function Login() {
  const { loginWithToken } = useContext(AuthContext);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      // DRF obtain_auth_token expects form-encoded or JSON; we'll send JSON
      const res = await client.post("/api-token-auth/", { username, password });
      const token = res.data.token;
      if (!token) throw new Error("No token returned");
      loginWithToken(token);
      alert("Logged in (token saved).");
    } catch (err) {
      console.error(err);
      alert("Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{maxWidth:420}}>
      <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" required />
      <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" required />
      <button type="submit" disabled={busy}>{busy ? "Logging in..." : "Login"}</button>
    </form>
  );
}
