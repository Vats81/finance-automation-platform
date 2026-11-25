"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { csvRow } from "@/lib/csv";
import { downloadProfitLossPdf, getDashboardTrend, sendReportEmail, sendReportWhatsApp } from "@/lib/api/dashboard";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import {
  DASHBOARD_PERIODS,
  DashboardGranularity,
  DashboardPeriod,
  DashboardTrendPoint,
  PERIOD_KEYS,
} from "@/types/dashboard";

const GRANULARITIES: { value: DashboardGranularity; label: MessageKey }[] = [
  { value: "day", label: "rep.daily" },
  { value: "week", label: "rep.weekly" },
  { value: "month", label: "rep.monthly" },
];

function toISODate(d: Date): string {
  // Local getters, not toISOString (which converts to UTC and shifts the
  // date by a day in positive-UTC-offset timezones) — same fix as
  // dashboard/page.tsx's toISODate.
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getPeriodRange(period: DashboardPeriod): { startDate: string; endDate: string } {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  if (period === "all_time") {
    const start = new Date(year, month - 11, 1);
    return { startDate: toISODate(start), endDate: toISODate(now) };
  }

  const start =
    period === "this_month"
      ? new Date(year, month, 1)
      : period === "this_quarter"
        ? new Date(year, Math.floor(month / 3) * 3, 1)
        : new Date(year, 0, 1);

  return { startDate: toISODate(start), endDate: toISODate(now) };
}

function formatPeriodLabel(
  periodStart: string,
  granularity: DashboardGranularity,
  locale = "en-US"
): string {
  const start = new Date(`${periodStart}T00:00:00`);

  if (granularity === "day") {
    return start.toLocaleDateString(locale, { month: "short", day: "numeric", year: "numeric" });
  }
  if (granularity === "month") {
    return start.toLocaleDateString(locale, { month: "long", year: "numeric" });
  }

  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  const startLabel = start.toLocaleDateString(locale, { month: "short", day: "numeric" });
  const endLabel = end.toLocaleDateString(locale, { month: "short", day: "numeric", year: "numeric" });
  return `${startLabel} – ${endLabel}`;
}

function downloadCsv(rows: DashboardTrendPoint[], granularity: DashboardGranularity): void {
  const header = ["Period", "Revenue", "Expenses", "Net Profit"];
  const lines = rows.map((row) => {
    const netProfit = Number(row.revenue) - Number(row.expenses);
    return [formatPeriodLabel(row.period_start, granularity), row.revenue, row.expenses, netProfit.toFixed(2)];
  });
  const totalRevenue = rows.reduce((sum, r) => sum + Number(r.revenue), 0);
  const totalExpenses = rows.reduce((sum, r) => sum + Number(r.expenses), 0);
  lines.push(["Total", totalRevenue.toFixed(2), totalExpenses.toFixed(2), (totalRevenue - totalExpenses).toFixed(2)]);

  const csv = [header, ...lines].map(csvRow).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `profit-and-loss-${granularity}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const { t, lang } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  // Viewers are read-only in the beta: they can see the numbers but not export or send them.
  const canExport = currentBusiness?.role !== "viewer";
  const [period, setPeriod] = useState<DashboardPeriod>("this_year");
  const [granularity, setGranularity] = useState<DashboardGranularity>("month");
  const [points, setPoints] = useState<DashboardTrendPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [emailStatus, setEmailStatus] = useState<string | null>(null);
  const [recipientPhone, setRecipientPhone] = useState("");
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState(false);
  const [whatsAppStatus, setWhatsAppStatus] = useState<string | null>(null);

  const [retryToken, setRetryToken] = useState(0);
  // Separate from `error` (used by the PDF/email/WhatsApp actions below) so
  // a failed send after the report already loaded doesn't blank out the
  // table that's already on screen.
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    setPoints(null);
    setError(null);
    setLoadError(null);
    const range = getPeriodRange(period);
    getDashboardTrend(getAccessToken(), currentBusinessId, { ...range, granularity })
      .then((res) => setPoints(res.points))
      .catch((err) => setLoadError(err instanceof Error ? err.message : t("s.failed_to_load_report")));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, period, granularity, getAccessToken, retryToken]);

  const hasActivity = points?.some((p) => Number(p.revenue) !== 0 || Number(p.expenses) !== 0);
  const totalRevenue = points?.reduce((sum, p) => sum + Number(p.revenue), 0) ?? 0;
  const totalExpenses = points?.reduce((sum, p) => sum + Number(p.expenses), 0) ?? 0;

  async function handleDownloadPdf() {
    if (!currentBusinessId) return;
    setIsDownloadingPdf(true);
    try {
      const range = getPeriodRange(period);
      await downloadProfitLossPdf(getAccessToken(), currentBusinessId, { ...range, granularity });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_download_pdf"));
    } finally {
      setIsDownloadingPdf(false);
    }
  }

  async function handleSendEmail() {
    if (!currentBusinessId || !recipientEmail) return;
    setIsSendingEmail(true);
    setEmailStatus(null);
    try {
      const range = getPeriodRange(period);
      await sendReportEmail(getAccessToken(), currentBusinessId, {
        recipientEmail,
        ...range,
        granularity,
      });
      setEmailStatus(t("x.sent"));
    } catch (err) {
      setEmailStatus(err instanceof Error ? err.message : t("s.failed_to_send_email"));
    } finally {
      setIsSendingEmail(false);
    }
  }

  async function handleSendWhatsApp() {
    if (!currentBusinessId || !recipientPhone) return;
    setIsSendingWhatsApp(true);
    setWhatsAppStatus(null);
    try {
      const range = getPeriodRange(period);
      await sendReportWhatsApp(getAccessToken(), currentBusinessId, {
        recipientPhone,
        ...range,
        granularity,
      });
      setWhatsAppStatus(t("x.sent"));
    } catch (err) {
      setWhatsAppStatus(err instanceof Error ? err.message : t("s.failed_to_send_whatsapp_message"));
    } finally {
      setIsSendingWhatsApp(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-1 text-2xl font-semibold">{t("nav.reports")}</h1>
          <p className="text-sm text-slate-500">{t("s.profit_loss_broken_down_by_the_per")}</p>
        </div>
        <div className="flex gap-3">
          <div className="w-40">
            <Select value={period} onChange={(e) => setPeriod(e.target.value as DashboardPeriod)}>
              {DASHBOARD_PERIODS.map((p) => (
                <option key={p.value} value={p.value}>
                  {t(PERIOD_KEYS[p.value])}
                </option>
              ))}
            </Select>
          </div>
          <div className="w-36">
            <Select
              value={granularity}
              onChange={(e) => setGranularity(e.target.value as DashboardGranularity)}
            >
              {GRANULARITIES.map((g) => (
                <option key={g.value} value={g.value}>
                  {t(g.label)}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <Card>
        {loadError ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-red-600">{loadError}</p>
            <Button variant="secondary" onClick={() => setRetryToken((n) => n + 1)}>
              {t("common.retry")}
            </Button>
          </div>
        ) : !points ? (
          <p className="text-sm text-slate-500">{t("s.loading")}</p>
        ) : hasActivity ? (
          <>
            {canExport ? (
              <div className="mb-4 flex justify-end gap-3">
                <Button variant="secondary" onClick={() => downloadCsv(points, granularity)}>
                  {t("s.download_csv")}
                </Button>
                <Button variant="secondary" onClick={handleDownloadPdf} disabled={isDownloadingPdf}>
                  {isDownloadingPdf ? t("s.downloading") : t("s.download_pdf")}
                </Button>
              </div>
            ) : (
              <p className="mb-4 text-right text-xs text-slate-500">
                {t("s.your_role_is_view_only_owners_admi")}
              </p>
            )}
            <div className="max-h-[500px] overflow-y-auto overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-4">{t("s.period")}</th>
                    <th className="py-2 pr-4">{t("dash.chartRevenue")}</th>
                    <th className="py-2 pr-4">{t("nav.expenses")}</th>
                    <th className="py-2 pr-4">{t("dash.profit")}</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((point) => {
                    const netProfit = Number(point.revenue) - Number(point.expenses);
                    return (
                      <tr key={point.period_start} className="border-b border-slate-100 last:border-0">
                        <td className="py-2 pr-4">{formatPeriodLabel(point.period_start, granularity, lang === "hi" ? "hi-IN" : "en-US")}</td>
                        <td className="py-2 pr-4 text-slate-600">{formatCurrency(point.revenue)}</td>
                        <td className="py-2 pr-4 text-slate-600">{formatCurrency(point.expenses)}</td>
                        <td className="py-2 pr-4 text-slate-600">{formatCurrency(netProfit)}</td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-slate-300 font-semibold">
                    <td className="py-2 pr-4">{t("common.total")}</td>
                    <td className="py-2 pr-4">{formatCurrency(totalRevenue)}</td>
                    <td className="py-2 pr-4">{formatCurrency(totalExpenses)}</td>
                    <td className="py-2 pr-4">{formatCurrency(totalRevenue - totalExpenses)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500">
            {t("rep.noData")}{" "}
            <Link href="/app/sales/new" className="text-brand-600 underline">
              {t("dash.recordSale")}
            </Link>
            {" · "}
            <Link href="/app/expenses/new" className="text-brand-600 underline">
              {t("dash.recordExpense")}
            </Link>
          </p>
        )}
      </Card>

      {points && hasActivity && canExport && (
        <Card className="mt-6">
          <h2 className="mb-4 text-sm font-semibold">{t("s.send_report")}</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder={t("s.owner_example_com")}
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                />
                <Button
                  variant="secondary"
                  onClick={handleSendEmail}
                  disabled={isSendingEmail || !recipientEmail}
                >
                  {isSendingEmail ? t("s.sending") : t("s.email_report")}
                </Button>
              </div>
              {emailStatus && <p className="mt-1 text-xs text-slate-500">{emailStatus}</p>}
            </div>
            <div>
              <div className="flex gap-2">
                <Input
                  type="tel"
                  placeholder="+91 98765 43210"
                  value={recipientPhone}
                  onChange={(e) => setRecipientPhone(e.target.value)}
                />
                <Button
                  variant="secondary"
                  onClick={handleSendWhatsApp}
                  disabled={isSendingWhatsApp || !recipientPhone}
                >
                  {isSendingWhatsApp ? t("s.sending") : t("s.send_via_whatsapp")}
                </Button>
              </div>
              {whatsAppStatus && <p className="mt-1 text-xs text-slate-500">{whatsAppStatus}</p>}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
