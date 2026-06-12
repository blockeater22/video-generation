import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { setToken } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [org, setOrg] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | authed | guest

  const loadMe = useCallback(async () => {
    try {
      const data = await api.me();
      setUser(data.user);
      setOrg(data.org);
      setStatus("authed");
    } catch {
      setUser(null);
      setOrg(null);
      setStatus("guest");
    }
  }, []);

  useEffect(() => {
    if (localStorage.getItem("access_token")) loadMe();
    else setStatus("guest");
  }, [loadMe]);

  const login = async (body) => {
    const data = await api.login(body);
    setToken(data.access_token);
    setUser(data.user);
    await loadMe();
    return data;
  };

  const register = async (body) => {
    const data = await api.register(body);
    setToken(data.access_token);
    setUser(data.user);
    await loadMe();
    return data;
  };

  const logout = async () => {
    try { await api.logout(); } catch { /* ignore */ }
    setToken(null);
    setUser(null);
    setOrg(null);
    setStatus("guest");
  };

  return (
    <AuthContext.Provider value={{ user, org, status, login, register, logout, refreshOrg: loadMe }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
