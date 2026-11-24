"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { completeOnboarding } from "@/lib/api/business";
import { getWhatsAppSummary, SummaryPeriod, WhatsAppSummary } from "@/lib/api/dashboard";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { LANGUAGES, Language, useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import { whatsappLink, whatsappPhone } from "@/lib/whatsapp";
import { SummaryFrequency } from "@/types/business";

const PERIODS: { value: SummaryPeriod; label: MessageKey }[] = [
  { value: "yesterday", label: "summary.yesterday" },
  { value: "today", label: "summary.today" },
  { value: "week", label: "summary.week" },
];

const FREQUENCIES: { value: SummaryFrequency; label: MessageKey }[] = [
  { value: "off", label: "summary.freqOff" },
  { value: "daily", label: "summary.freqDaily" },
  { value: "weekly", label: "summary.freqWeekly" },
];

export default function WhatsAppSummaryPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness, refresh } = useCurrentBusiness();
  const { t, lang } = useT();
  const business = currentBusiness?.business;
  const [period, setPeriod] = useState<SummaryPeriod>("yesterday");
  const [summary, setSummary] = useState<WhatsAppSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!currentBusinessId) return;
    setSummary(null);
    setError(null);
    // The preview is written in the language the page is in, so what you see is what you send.
    getWhatsAppSummary(getAccessToken(), currentBusinessId, period, lang)
      .then(setSummary)
      .catch((err) => setError(err instanceof Error ? err.message : t("summary.loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken, period, lang]);

  const ownPhone = whatsappPhone(business?.whatsapp_number);

  async function save(body: { summary_frequency?: SummaryFrequency; language?: Language }) {
    if (!currentBusinessId) return;
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      await completeOnboarding(getAccessToken(), currentBusinessId, body);
      await refresh();
      setNotice(
        body.summary_frequency === "off"
          ? t("summary.autoOff")
          : body.summary_frequency
            ? t("summary.autoSaved")
            : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t("summary.saveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  async function copyText() {
    if (!summary) return;
    try {
      await navigator.clipboard.writeText(summary.message);
      setNotice(t("summary.copied"));
    } catch {
      setNotice(t("summary.copyFailed"));
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">{t("summary.title")}</h1>
      <p className="mb-6 text-sm text-slate-500">{t("summary.subtitle")}</p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {notice && <p className="mb-4 text-sm text-green-700">{notice}</p>}

      <Card className="mb-6 max-w-xl">
        <div className="mb-4 grid grid-cols-3 gap-2" role="radiogroup" aria-label={t("common.date")}>
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              role="radio"
              aria-checked={period === p.value}
              onClick={() => setPeriod(p.value)}
              className={`rounded-md border px-2 py-2 text-sm font-medium ${
                period === p.value
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-slate-300 bg-white text-slate-700"
              }`}
            >
              {t(p.label)}
            </button>
          ))}
        </div>

        {!summary && !error ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : (
          summary && (
            <>
              <pre className="mb-4 whitespace-pre-wrap rounded-md bg-green-50 p-4 font-sans text-sm text-slate-800">
                {summary.message}
              </pre>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => window.open(whatsappLink(ownPhone, summary.message), "_blank")}>
                  {ownPhone ? t("summary.sendMine") : t("summary.send")}
                </Button>
                <Button variant="secondary" onClick={copyText}>
                  {t("summary.copy")}
                </Button>
              </div>
              {!ownPhone && (
                <p className="mt-3 text-xs text-slate-500">
                  <Link href="/app/settings" className="underline">
                    {t("summary.addNumber")}
                  </Link>
                </p>
              )}
            </>
          )
        )}
      </Card>

      <Card className="max-w-xl">
        <h2 className="mb-1 text-base font-semibold">{t("summary.autoTitle")}</h2>
        <p className="mb-3 text-sm text-slate-500">
          {t("summary.autoText")}
          {!ownPhone && ` ${t("summary.autoNeedNumber")}`}
        </p>
        <Select
          aria-label={t("summary.autoTitle")}
          value={business?.summary_frequency ?? "off"}
          disabled={isSaving || !ownPhone}
          onChange={(e) => void save({ summary_frequency: e.target.value as SummaryFrequency })}
        >
          {FREQUENCIES.map((f) => (
            <option key={f.value} value={f.value}>
              {t(f.label)}
            </option>
          ))}
        </Select>
        <label className="mt-4 block text-sm font-medium">{t("summary.language")}</label>
        <Select
          aria-label={t("summary.language")}
          value={business?.language ?? "en"}
          disabled={isSaving}
          onChange={(e) => void save({ language: e.target.value as Language })}
          className="mt-1"
        >
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </Select>
        <p className="mt-3 text-xs text-slate-500">{t("summary.autoNote")}</p>
      </Card>
    </div>
  );
}
