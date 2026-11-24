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
import { whatsappLink, whatsappPhone } from "@/lib/whatsapp";
import { SummaryFrequency } from "@/types/business";

const PERIODS: { value: SummaryPeriod; label: string }[] = [
  { value: "yesterday", label: "Yesterday" },
  { value: "today", label: "Today so far" },
  { value: "week", label: "Last 7 days" },
];

const FREQUENCIES: { value: SummaryFrequency; label: string }[] = [
  { value: "off", label: "Off" },
  { value: "daily", label: "Every morning (yesterday's numbers)" },
  { value: "weekly", label: "Every Monday (the last 7 days)" },
];

export default function WhatsAppSummaryPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness, refresh } = useCurrentBusiness();
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
    getWhatsAppSummary(getAccessToken(), currentBusinessId, period)
      .then(setSummary)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load the summary"));
  }, [currentBusinessId, getAccessToken, period]);

  const ownPhone = whatsappPhone(business?.whatsapp_number);

  async function saveFrequency(value: SummaryFrequency) {
    if (!currentBusinessId) return;
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      await completeOnboarding(getAccessToken(), currentBusinessId, { summary_frequency: value });
      await refresh();
      setNotice(value === "off" ? "Automatic summaries are off." : "Saved. The summary will be sent on its own.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setIsSaving(false);
    }
  }

  async function copyText() {
    if (!summary) return;
    try {
      await navigator.clipboard.writeText(summary.message);
      setNotice("Copied. Paste it anywhere.");
    } catch {
      setNotice("Could not copy. Select the text and copy it.");
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">WhatsApp summary</h1>
      <p className="mb-6 text-sm text-slate-500">
        Sales, expenses, profit and who owes you money, in one WhatsApp message.
      </p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {notice && <p className="mb-4 text-sm text-green-700">{notice}</p>}

      <Card className="mb-6 max-w-xl">
        <div className="mb-4 grid grid-cols-3 gap-2" role="radiogroup" aria-label="Period">
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
              {p.label}
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
                  {ownPhone ? "Send to my WhatsApp" : "Send on WhatsApp"}
                </Button>
                <Button variant="secondary" onClick={copyText}>
                  Copy text
                </Button>
              </div>
              {!ownPhone && (
                <p className="mt-3 text-xs text-slate-500">
                  Add your WhatsApp number in{" "}
                  <Link href="/app/settings" className="underline">
                    Settings
                  </Link>{" "}
                  to send it straight to yourself.
                </p>
              )}
            </>
          )
        )}
      </Card>

      <Card className="max-w-xl">
        <h2 className="mb-1 text-base font-semibold">Send it to me automatically</h2>
        <p className="mb-3 text-sm text-slate-500">
          Finverlo can send this to your WhatsApp number on its own, so you do not have to open the app.
          {!ownPhone && " Add your WhatsApp number in Settings first."}
        </p>
        <Select
          aria-label="Automatic summary"
          value={business?.summary_frequency ?? "off"}
          disabled={isSaving || !ownPhone}
          onChange={(e) => void saveFrequency(e.target.value as SummaryFrequency)}
        >
          {FREQUENCIES.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </Select>
        <p className="mt-3 text-xs text-slate-500">
          Automatic sending depends on Finverlo&apos;s WhatsApp connection being switched on for your account.
          Until it is, use the button above whenever you want the summary.
        </p>
      </Card>
    </div>
  );
}
