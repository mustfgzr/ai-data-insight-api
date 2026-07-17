import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import type { User } from "./types";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const TOKEN_KEY = "data-insight-token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setReady(true);
      return;
    }
    api.me(token).then(setUser).catch(() => {
      sessionStorage.removeItem(TOKEN_KEY);
      setToken(null);
    }).finally(() => setReady(true));
  }, [token]);

  const saveSession = async (email: string, password: string) => {
    const result = await api.login(email, password);
    sessionStorage.setItem(TOKEN_KEY, result.access_token);
    setToken(result.access_token);
  };

  const value = useMemo<AuthContextValue>(() => ({
    token,
    user,
    ready,
    signIn: saveSession,
    register: async (email, password) => {
      await api.register(email, password);
      await saveSession(email, password);
    },
    signOut: () => {
      sessionStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
    },
  }), [token, user, ready]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
