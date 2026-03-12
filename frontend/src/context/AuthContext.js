import { createContext, useState, useEffect } from "react";
import api from "../services/api";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  // LOGIN
  const login = async (data) => {
    try {
      const res = await api.post("/api/token/", {
        username: data.username,
        password: data.password
      });

      localStorage.setItem("access", res.data.access);
      localStorage.setItem("refresh", res.data.refresh);

      setUser(data.username);
    } catch (error) {
      console.error("Login failed:", error.response?.data || error.message);
      throw error;
    }
  };

  // REGISTER
  const register = async (data) => {
    await api.post("/api/accounts/register/", data);
  };

  // LOGOUT
  const logout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  };

  // FETCH CURRENT USER
  const getUser = async () => {
    try {
      const res = await api.get("/api/accounts/me/");
      setUser(res.data.username);
    } catch {
      console.log("Could not fetch user");
    }
  };

  // AUTO LOGIN IF TOKEN EXISTS
  useEffect(() => {
    if (localStorage.getItem("access")) {
      getUser();
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};