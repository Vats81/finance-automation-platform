"use client";

import { LANGUAGES, useT } from "@/lib/i18n/LanguageProvider";

/** A two-button English / हिन्दी switch. The choice is remembered on this device. */
export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { lang, setLang } = useT();
  return (
    <div
      role="group"
      aria-label="Language"
      className={`inline-flex overflow-hidden rounded-md border border-slate-300 text-sm ${className}`}
    >
      {LANGUAGES.map((l) => (
        <button
          key={l.code}
          type="button"
          onClick={() => setLang(l.code)}
          aria-pressed={lang === l.code}
          title={l.label}
          className={`px-2.5 py-1.5 font-medium ${
            lang === l.code ? "bg-brand-600 text-white" : "bg-white text-slate-700 hover:bg-slate-50"
          }`}
        >
          {l.short}
        </button>
      ))}
    </div>
  );
}
