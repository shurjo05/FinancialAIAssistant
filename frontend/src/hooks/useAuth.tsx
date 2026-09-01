import { createContext, useContext, useState, type ReactNode } from "react";
import { api, clearToken, getToken } from "../services/api";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(getToken());

  const login = async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    setTok(access_token);
  };

  const register = async (email: string, password: string) => {
    await api.register(email, password);
    await login(email, password); // auto-login after registering
  };

  const logout = () => {
    clearToken();
    setTok(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
