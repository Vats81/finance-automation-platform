"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { listMyBusinesses } from "@/lib/api/business";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { MyBusinessResponse } from "@/types/business";

const STORAGE_KEY = "fap.smb.currentBusinessId";

interface CurrentBusinessState {
  businesses: MyBusinessResponse[];
  currentBusinessId: string | null;
  currentBusiness: MyBusinessResponse | null;
  isLoading: boolean;
  setCurrentBusinessId: (businessId: string) => void;
  refresh: () => Promise<void>;
}

const CurrentBusinessContext = createContext<CurrentBusinessState | null>(null);

/**
 * Drives the business switcher and every SMB page's "which business am I
 * looking at" question — a platform user can belong to multiple businesses
 * (BusinessMembership, backend/app/business/), so the active one is kept
 * here rather than re-derived per page.
 */
export function CurrentBusinessProvider({ children }: { children: React.ReactNode }) {
  const { getAccessToken, isAuthenticated, isLoading: authLoading } = useLocalAuth();
  const [businesses, setBusinesses] = useState<MyBusinessResponse[]>([]);
  const [currentBusinessId, setCurrentBusinessIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    // useLocalAuth() hydrates its session from localStorage in its own
    // effect, so on first mount isAuthenticated is transiently false even
    // for an already-logged-in user — bailing out here before that
    // hydration finishes previously caused every fresh page load to see
    // zero businesses and get bounced to onboarding. Wait for it instead
    // of treating "not loaded yet" as "not authenticated".
    if (authLoading) return;
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    const token = getAccessToken();
    const mine = await listMyBusinesses(token);
    setBusinesses(mine);

    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const stillValid = mine.some((m) => m.business.id === stored);
    const nextId = stillValid ? stored : (mine[0]?.business.id ?? null);
    setCurrentBusinessIdState(nextId);
    if (nextId) localStorage.setItem(STORAGE_KEY, nextId);
    setIsLoading(false);
  }, [getAccessToken, isAuthenticated, authLoading]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setCurrentBusinessId = useCallback((businessId: string) => {
    localStorage.setItem(STORAGE_KEY, businessId);
    setCurrentBusinessIdState(businessId);
  }, []);

  const currentBusiness = businesses.find((m) => m.business.id === currentBusinessId) ?? null;

  return (
    <CurrentBusinessContext.Provider
      value={{ businesses, currentBusinessId, currentBusiness, isLoading, setCurrentBusinessId, refresh }}
    >
      {children}
    </CurrentBusinessContext.Provider>
  );
}

export function useCurrentBusiness(): CurrentBusinessState {
  const ctx = useContext(CurrentBusinessContext);
  if (!ctx) throw new Error("useCurrentBusiness must be used within CurrentBusinessProvider");
  return ctx;
}
