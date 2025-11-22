import React, { createContext, useState, useEffect } from "react";
import { setAuthToken } from "./api/client";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token") || null);
  useEffect(() => setAuthToken(token), [token]);
  function loginWithToken(t) {
    localStorage.setItem("token", t);
    setToken(t);
  }
  function logout() {
    localStorage.removeItem("token");
    setToken(null);
  }
  return (
    <AuthContext.Provider value={{ token, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
