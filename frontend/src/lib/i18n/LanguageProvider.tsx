"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { MessageKey, messages } from "@/lib/i18n/messages";

export type Language = "en" | "hi";

export const LANGUAGES: { code: Language; label: string; short: string }[] = [
  { code: "en", label: "English", short: "EN" },
  { code: "hi", label: "हिन्दी", short: "हिं" },
];

const STORAGE_KEY = "finverlo.lang";

type Vars = Record<string, string | number>;

interface LanguageContextValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: MessageKey, vars?: Vars) => string;
  /** The text for a value the server sends (a status, a role): `${prefix}.${value}` if there is one, else the value. */
  label: (prefix: string, value: string) => string;
}

/** Fills {name}-style placeholders. A placeholder with no value is left as written. */
export function translate(lang: Language, key: MessageKey, vars?: Vars): string {
  const text = messages[key][lang === "hi" ? 1 : 0];
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name: string) => (name in vars ? String(vars[name]) : whole));
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: "en",
  setLang: () => undefined,
  t: (key, vars) => translate("en", key, vars),
  label: (_prefix, value) => value.replace(/_/g, " "),
});

function initialLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "hi") return stored;
  } catch {
    // storage blocked: fall through to the browser's language
  }
  // Someone whose phone is set to Hindi starts in Hindi; anyone can switch from the top bar.
  return typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("hi") ? "hi" : "en";
}

/**
 * The page language. It starts as English on the server and on first paint (so the page matches what the
 * server sent), then switches to the saved or browser language straight after.
 */
export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>("en");

  useEffect(() => {
    setLangState(initialLanguage());
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Language) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // not saved, still applies until the page is closed
    }
  }, []);

  const value = useMemo<LanguageContextValue>(
    () => ({
      lang,
      setLang,
      t: (key, vars) => translate(lang, key, vars),
      label: (prefix, value) => {
        const key = `${prefix}.${value}`;
        return key in messages ? translate(lang, key as MessageKey) : value.replace(/_/g, " ");
      },
    }),
    [lang, setLang]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useT(): LanguageContextValue {
  return useContext(LanguageContext);
}
