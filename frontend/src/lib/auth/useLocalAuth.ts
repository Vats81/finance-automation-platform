"use client";

import { useCallback, useEffect, useState } from "react";
import { loginUser } from "@/lib/api/auth";
import { LocalUserResponse } from "@/types/auth";

// Local (email+password) auth for the SMB Finance Manager product —
// entirely independent of useAuth.ts (MSAL/Entra + dev-mode bypass), which
// remains exactly as-is for the existing AP-automation product. Both can
// coexist in the same Next.js app because they use different storage keys
// and different API routes (/auth/* here vs. Entra's own token flow).

const STORAGE_KEY = "fap.localAuth.session";

interface LocalSession {
  accessToken: string;
  expiresAt: string;
  user: LocalUserResponse;
}

function loadSession(): LocalSession | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as LocalSession;
    if (new Date(session.expiresAt).getTime() <= Date.now()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

function saveSession(session: LocalSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

interface LocalAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: LocalUserResponse | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  getAccessToken: () => string | null;
}

export function useLocalAuth(): LocalAuthState {
  const [session, setSession] = useState<LocalSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setSession(loadSession());
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginUser({ email, password });
    const next: LocalSession = {
      accessToken: result.access_token,
      expiresAt: result.expires_at,
      user: result.user,
    };
    saveSession(next);
    setSession(next);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const getAccessToken = useCallback((): string | null => {
    return loadSession()?.accessToken ?? null;
  }, []);

  return {
    isAuthenticated: session !== null,
    isLoading,
    user: session?.user ?? null,
    login,
    logout,
    getAccessToken,
  };
}
