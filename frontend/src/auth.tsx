import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import type { User } from "./types";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<User>;
  register: (fullName: string, email: string, password: string) => Promise<User>;
  updateUser: (user: User) => void;
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
    const currentUser = await api.me(result.access_token);
    setUser(currentUser);
    return currentUser;
  };

  const value = useMemo<AuthContextValue>(() => ({
    token,
    user,
    ready,
    signIn: saveSession,
    register: async (fullName, email, password) => {
      await api.register(fullName, email, password);
      return saveSession(email, password);
    },
    updateUser: setUser,
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
