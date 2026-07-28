"use client";

import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { apiTokenRequest, isAuthDevMode } from "@/lib/auth/msalConfig";
import { buildDevToken, clearDevSession, DevSession, loadDevSession, saveDevSession } from "@/lib/auth/devAuth";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  devSession: DevSession | null;
  loginDev: (session: DevSession) => void;
  loginMsal: () => Promise<void>;
  logout: () => void;
  getAccessToken: () => Promise<string | null>;
}

/**
 * Single auth surface the rest of the app uses, regardless of whether we're
 * running against real Entra ID (MSAL popup/redirect) or the local dev-mode
 * bypass. Keeping this switch in one hook means every other component only
 * ever calls `getAccessToken()` / `isAuthenticated` and never branches on
 * `isAuthDevMode` itself.
 */
export function useAuth(): AuthState {
  const msal = useMsal();
  const msalIsAuthenticated = useIsAuthenticated();
  const [devSession, setDevSession] = useState<DevSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (isAuthDevMode) {
      setDevSession(loadDevSession());
    }
    setIsLoading(false);
  }, []);

  const loginDev = useCallback((session: DevSession) => {
    saveDevSession(session);
    setDevSession(session);
  }, []);

  const loginMsal = useCallback(async () => {
    await msal.instance.loginRedirect(apiTokenRequest);
  }, [msal.instance]);

  const logout = useCallback(() => {
    if (isAuthDevMode) {
      clearDevSession();
      setDevSession(null);
    } else {
      void msal.instance.logoutRedirect();
    }
  }, [msal.instance]);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (isAuthDevMode) {
      const session = loadDevSession();
      return session ? buildDevToken(session) : null;
    }
    const account = msal.instance.getActiveAccount() ?? msal.accounts[0];
    if (!account) return null;
    try {
      const result = await msal.instance.acquireTokenSilent({ ...apiTokenRequest, account });
      return result.accessToken;
    } catch {
      await msal.instance.acquireTokenRedirect(apiTokenRequest);
      return null;
    }
  }, [msal.instance, msal.accounts]);

  return {
    isAuthenticated: isAuthDevMode ? devSession !== null : msalIsAuthenticated,
    isLoading,
    devSession,
    loginDev,
    loginMsal,
    logout,
    getAccessToken,
  };
}
