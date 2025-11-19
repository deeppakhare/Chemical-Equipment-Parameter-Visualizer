import React, { useState } from "react";
import { loginMock } from "../api/mockServer";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await loginMock(username, password);
      onLogin(res.token);
    } catch (err) {
      console.error(err);
      alert("Login failed (mock)");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{maxWidth:420}}>
      <h3>Sign in (mock)</h3>
      <div style={{marginBottom:8}}>
        <input
          placeholder="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          style={{width:"100%", padding:8}}
        />
      </div>
      <div style={{marginBottom:8}}>
        <input
          placeholder="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          required
          style={{width:"100%", padding:8}}
        />
      </div>
      <button type="submit" disabled={busy} style={{padding:"8px 12px"}}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <p style={{fontSize:12, color:"#666"}}>This is a mock login for frontend development.</p>
    </form>
  );
}
