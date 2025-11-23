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
      const res = await client.post("/api-token-auth/", { username, password });
      const token = res.data.token;
      if (!token) throw new Error("No token returned");
      loginWithToken(token);
      alert("Logged in (token saved).");
    } catch (err) {
      console.error(err);
      alert("Login failed: " + (err.response?.data || err.message || err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label style={{ textAlign: "left", fontSize: 13, color: "var(--muted)" }}>Username</label>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="username"
        required
      />
      <label style={{ textAlign: "left", fontSize: 13, color: "var(--muted)" }}>Password</label>
      <input
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="password"
        type="password"
        required
      />
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <button className="btn" type="submit" disabled={busy}>{busy ? "Logging in..." : "Login"}</button>
        <button
          type="button"
          className="btn secondary"
          onClick={() => {
            setUsername("demo");
            setPassword("demo");
          }}
        >
          Fill demo
        </button>
      </div>
    </form>
  );
}
