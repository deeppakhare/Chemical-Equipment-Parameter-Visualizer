// web/src/AuthContext.jsx
import React, { createContext, useState, useEffect, useMemo } from "react";
import { setAuthToken } from "./api/client";

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token") || null);

  // memoize context value to avoid re-renders
  const value = useMemo(() => {
    return {
      token,
      loginWithToken: (t) => {
        localStorage.setItem("token", t);
        setToken(t);
      },
      logout: () => {
        localStorage.removeItem("token");
        setToken(null);
      }
    };
  }, [token]);

  // sync axios header
  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
