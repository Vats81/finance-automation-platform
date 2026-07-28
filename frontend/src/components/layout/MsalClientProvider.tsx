"use client";

import { EventType, PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { useEffect, useState } from "react";
import { isAuthDevMode, msalConfig } from "@/lib/auth/msalConfig";

/**
 * Instantiates MSAL client-side only. In AUTH_DEV_MODE we still mount the
 * provider (msal-react's hooks are used unconditionally in useAuth) but
 * skip calling `initialize()`/interactive flows, since there is no real
 * Entra App Registration configured for local dev.
 */
export function MsalClientProvider({ children }: { children: React.ReactNode }) {
  const [msalInstance] = useState(() => new PublicClientApplication(msalConfig));
  const [isInitialized, setIsInitialized] = useState(isAuthDevMode);

  useEffect(() => {
    if (isAuthDevMode) return;

    msalInstance.initialize().then(() => {
      const accounts = msalInstance.getAllAccounts();
      if (accounts[0]) msalInstance.setActiveAccount(accounts[0]);

      msalInstance.addEventCallback((event) => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
          const account = (event.payload as { account?: unknown }).account;
          if (account) msalInstance.setActiveAccount(account as never);
        }
      });

      setIsInitialized(true);
    });
  }, [msalInstance]);

  if (!isInitialized) return null;

  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
}
