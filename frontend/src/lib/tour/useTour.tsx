"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { MessageKey } from "@/lib/i18n/messages";

const STORAGE_KEY = "fap.tour.completed";

export interface TourStep {
  title: MessageKey;
  body: MessageKey;
}

export const TOUR_STEPS: TourStep[] = [
  { title: "tour.1.title", body: "tour.1.body" },
  { title: "tour.2.title", body: "tour.2.body" },
  { title: "tour.3.title", body: "tour.3.body" },
  { title: "tour.4.title", body: "tour.4.body" },
  { title: "tour.5.title", body: "tour.5.body" },
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
