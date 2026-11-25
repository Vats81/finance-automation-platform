"use client";

import { useT } from "@/lib/i18n/LanguageProvider";

export function Spinner({ className = "" }: { className?: string }) {
  const { t } = useT();
  return (
    <div
      className={`h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600 ${className}`}
      role="status"
      aria-label={t("common.loading")}
    />
  );
}
