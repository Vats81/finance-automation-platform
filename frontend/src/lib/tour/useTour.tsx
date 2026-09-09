"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "fap.tour.completed";

export interface TourStep {
  title: string;
  body: string;
}

export const TOUR_STEPS: TourStep[] = [
  {
    title: "Welcome to FinanceAI",
    body: "This is your business dashboard — revenue, expenses, and health score update automatically as you record activity.",
  },
  {
    title: "Record a sale, purchase, or expense",
    body: "Use the sidebar to record sales, purchases, and expenses. Each supports line items, an optional customer or vendor, and payment tracking.",
  },
  {
    title: "Edit or void anytime",
    body: "Made a mistake? Open any sale or purchase and click Edit to change it, or Void to close it out without deleting your records.",
  },
  {
    title: "Reports & the AI Assistant",
    body: "Reports gives you a Profit & Loss breakdown you can export or send by email/WhatsApp. The AI Assistant answers questions about your own numbers.",
  },
  {
    title: "Need help later?",
    body: "Visit Help in the sidebar anytime for a written walkthrough of every feature, or replay this tour from there.",
  },
];

interface TourState {
  isOpen: boolean;
  stepIndex: number;
  steps: TourStep[];
  next: () => void;
  back: () => void;
  skip: () => void;
  restart: () => void;
}

const TourContext = createContext<TourState | null>(null);

/**
 * First-visit guided tour: a sequential centered-modal walkthrough (not a
 * DOM-anchored spotlight/tooltip tour — see the plan's reasoning for why
 * that scope was deliberately avoided). Backed by localStorage, same
 * per-viewer-state convention as CurrentBusinessContext.tsx's business
 * selection.
 */
export function TourProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) !== "true") {
        setIsOpen(true);
      }
    } catch {
      // localStorage unavailable (private browsing, blocked site data, ...) — skip the tour.
    }
  }, []);

  const complete = useCallback(() => {
    setIsOpen(false);
    setStepIndex(0);
    try {
      localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // ignore — worst case the tour reappears next visit
    }
  }, []);

  const next = useCallback(() => {
    setStepIndex((i) => Math.min(i + 1, TOUR_STEPS.length - 1));
  }, []);

  const back = useCallback(() => {
    setStepIndex((i) => Math.max(i - 1, 0));
  }, []);

  const restart = useCallback(() => {
    setStepIndex(0);
    setIsOpen(true);
  }, []);

  return (
    <TourContext.Provider
      value={{ isOpen, stepIndex, steps: TOUR_STEPS, next, back, skip: complete, restart }}
    >
      {children}
    </TourContext.Provider>
  );
}

export function useTour(): TourState {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error("useTour must be used within TourProvider");
  return ctx;
}
