import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import * as authApi from "../lib/auth";
import { setTokens, clearTokens, getAccessToken } from "../lib/api";

interface AuthContextValue {
  user: authApi.CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (orgName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<authApi.CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      if (getAccessToken()) {
        try {
          const currentUser = await authApi.getMe();
          setUser(currentUser);
        } catch {
          clearTokens();
        }
      }
      setIsLoading(false);
    }
    restoreSession();

    function handleUnauthorized() {
      clearTokens();
      setUser(null);
    }

    window.addEventListener("secureops:unauthorized", handleUnauthorized);

    return () => {
      window.removeEventListener("secureops:unauthorized", handleUnauthorized);
    };
  }, []);

  async function login(email: string, password: string) {
    const tokens = await authApi.login(email, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    const currentUser = await authApi.getMe();
    setUser(currentUser);
  }

  async function register(orgName: string, email: string, password: string) {
    const tokens = await authApi.register(orgName, email, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    const currentUser = await authApi.getMe();
    setUser(currentUser);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth doit être utilisé à l'intérieur d'un AuthProvider");
  }
  return context;
}
