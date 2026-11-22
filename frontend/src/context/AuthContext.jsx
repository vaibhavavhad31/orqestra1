import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null = checking, false = signed out, object = signed in
  const [user, setUser] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    if (window.location.hash?.includes("session_id=")) return;
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    const onExpired = () => setUser(false);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const withUser = (promise) => promise.then(({ data }) => { setUser(data.user); return data.user; });

  const value = {
    user,
    setUser,
    refresh: checkAuth,
    login: (email, password) => withUser(api.post("/auth/login", { email, password })),
    register: (payload) => withUser(api.post("/auth/register", payload)),
    demoLogin: (key) => withUser(api.post("/demo/login", { key })),
    switchTo: (targetUserId) => withUser(api.post("/demo/switch", { target_user_id: targetUserId })),
    completeGoogle: (payload) => withUser(api.post("/auth/google/complete", payload)),
    logout: async () => {
      try { await api.post("/auth/logout"); } finally { setUser(false); }
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
