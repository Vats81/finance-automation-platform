"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { listMyBusinesses } from "@/lib/api/business";
import { listMyFirms } from "@/lib/api/firms";
import { setDisplayCurrency } from "@/lib/format";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { MyBusinessResponse } from "@/types/business";
import { FirmResponse } from "@/types/firm";

const STORAGE_KEY = "fap.smb.currentBusinessId";
const FIRM_STORAGE_KEY = "fap.smb.currentFirmId";

interface CurrentBusinessState {
  businesses: MyBusinessResponse[];
  currentBusinessId: string | null;
  currentBusiness: MyBusinessResponse | null;
  /** Accounting firms the user works for (empty for an ordinary business owner). */
  firms: FirmResponse[];
  currentFirm: FirmResponse | null;
  setCurrentFirmId: (firmId: string) => void;
  isLoading: boolean;
  setCurrentBusinessId: (businessId: string) => void;
  refresh: () => Promise<void>;
}

const CurrentBusinessContext = createContext<CurrentBusinessState | null>(null);

/**
 * Drives the business switcher and every SMB page's "which business am I
 * looking at" question — a platform user can belong to multiple businesses
 * (BusinessMembership, backend/app/business/), and an accounting-firm user
 * also reaches the firm's client businesses, so the active one is kept
 * here rather than re-derived per page.
 */
export function CurrentBusinessProvider({ children }: { children: React.ReactNode }) {
  const { getAccessToken, isAuthenticated, isLoading: authLoading } = useLocalAuth();
  const [businesses, setBusinesses] = useState<MyBusinessResponse[]>([]);
  const [firms, setFirms] = useState<FirmResponse[]>([]);
  const [currentBusinessId, setCurrentBusinessIdState] = useState<string | null>(null);
  const [currentFirmId, setCurrentFirmIdState] = useState<string | null>(null);
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
    const [mine, myFirms] = await Promise.all([
      listMyBusinesses(token),
      // A failure to load firms must never lock an ordinary business owner out.
      listMyFirms(token).catch(() => [] as FirmResponse[]),
    ]);
    setBusinesses(mine);
    setFirms(myFirms);

    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const stillValid = mine.some((m) => m.business.id === stored);
    const nextId = stillValid ? stored : (mine[0]?.business.id ?? null);
    setCurrentBusinessIdState(nextId);
    if (nextId) localStorage.setItem(STORAGE_KEY, nextId);

    const storedFirm = typeof window !== "undefined" ? localStorage.getItem(FIRM_STORAGE_KEY) : null;
    setCurrentFirmIdState(myFirms.some((f) => f.id === storedFirm) ? storedFirm : (myFirms[0]?.id ?? null));
    setIsLoading(false);
  }, [getAccessToken, isAuthenticated, authLoading]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setCurrentBusinessId = useCallback((businessId: string) => {
    localStorage.setItem(STORAGE_KEY, businessId);
    setCurrentBusinessIdState(businessId);
  }, []);

  const setCurrentFirmId = useCallback((firmId: string) => {
    localStorage.setItem(FIRM_STORAGE_KEY, firmId);
    setCurrentFirmIdState(firmId);
  }, []);

  const currentBusiness = businesses.find((m) => m.business.id === currentBusinessId) ?? null;
  // Set during render, before the children draw, so every amount on screen uses this business's currency.
  setDisplayCurrency(currentBusiness?.business.currency);
  const currentFirm = firms.find((f) => f.id === currentFirmId) ?? null;

  return (
    <CurrentBusinessContext.Provider
      value={{
        businesses,
        currentBusinessId,
        currentBusiness,
        firms,
        currentFirm,
        setCurrentFirmId,
        isLoading,
        setCurrentBusinessId,
        refresh,
      }}
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
