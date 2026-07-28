"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { downloadProfitLossPdf, getDashboardTrend, sendReportEmail, sendReportWhatsApp } from "@/lib/api/dashboard";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { DASHBOARD_PERIODS, DashboardGranularity, DashboardPeriod, DashboardTrendPoint } from "@/types/dashboard";

const GRANULARITIES: { value: DashboardGranularity; label: string }[] = [
  { value: "day", label: "Daily" },
  { value: "week", label: "Weekly" },
  { value: "month", label: "Monthly" },
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

function formatPeriodLabel(periodStart: string, granularity: DashboardGranularity): string {
  const start = new Date(`${periodStart}T00:00:00`);

  if (granularity === "day") {
    return start.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  if (granularity === "month") {
    return start.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }

  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  const startLabel = start.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const endLabel = end.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
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

  const csv = [header, ...lines].map((line) => line.join(",")).join("\n");
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
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
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

  useEffect(() => {
    if (!currentBusinessId) return;
    setPoints(null);
    setError(null);
    const range = getPeriodRange(period);
    getDashboardTrend(getAccessToken(), currentBusinessId, { ...range, granularity })
      .then((res) => setPoints(res.points))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load report"));
  }, [currentBusinessId, period, granularity, getAccessToken]);

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
      setError(err instanceof Error ? err.message : "Failed to download PDF");
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
      setEmailStatus("Sent!");
    } catch (err) {
      setEmailStatus(err instanceof Error ? err.message : "Failed to send email");
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
      setWhatsAppStatus("Sent!");
    } catch (err) {
      setWhatsAppStatus(err instanceof Error ? err.message : "Failed to send WhatsApp message");
    } finally {
      setIsSendingWhatsApp(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-1 text-2xl font-semibold">Reports</h1>
          <p className="text-sm text-slate-500">Profit &amp; Loss, broken down by the period you choose.</p>
        </div>
        <div className="flex gap-3">
          <div className="w-40">
            <Select value={period} onChange={(e) => setPeriod(e.target.value as DashboardPeriod)}>
              {DASHBOARD_PERIODS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
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
                  {g.label}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <Card>
        {!points && !error ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : points && hasActivity ? (
          <>
            <div className="mb-4 flex justify-end gap-3">
              <Button variant="secondary" onClick={() => downloadCsv(points, granularity)}>
                Download CSV
              </Button>
              <Button variant="secondary" onClick={handleDownloadPdf} disabled={isDownloadingPdf}>
                {isDownloadingPdf ? "Downloading..." : "Download PDF"}
              </Button>
            </div>
            <div className="max-h-[500px] overflow-y-auto overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-4">Period</th>
                    <th className="py-2 pr-4">Revenue</th>
                    <th className="py-2 pr-4">Expenses</th>
                    <th className="py-2 pr-4">Net profit</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((point) => {
                    const netProfit = Number(point.revenue) - Number(point.expenses);
                    return (
                      <tr key={point.period_start} className="border-b border-slate-100 last:border-0">
                        <td className="py-2 pr-4">{formatPeriodLabel(point.period_start, granularity)}</td>
                        <td className="py-2 pr-4 text-slate-600">{formatCurrency(point.revenue)}</td>
                        <td className="py-2 pr-4 text-slate-600">{formatCurrency(point.expenses)}</td>
                        <td className="py-2 pr-4 text-slate-600">{formatCurrency(netProfit)}</td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-slate-300 font-semibold">
                    <td className="py-2 pr-4">Total</td>
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
            Not enough data yet — import sales or expenses from the{" "}
            <Link href="/app/data-upload" className="text-brand-600 underline">
              Data Upload Centre
            </Link>{" "}
            to see a report here.
          </p>
        )}
      </Card>

      {points && hasActivity && (
        <Card className="mt-6">
          <h2 className="mb-4 text-sm font-semibold">Send report</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="owner@example.com"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                />
                <Button
                  variant="secondary"
                  onClick={handleSendEmail}
                  disabled={isSendingEmail || !recipientEmail}
                >
                  {isSendingEmail ? "Sending..." : "Email report"}
                </Button>
              </div>
              {emailStatus && <p className="mt-1 text-xs text-slate-500">{emailStatus}</p>}
            </div>
            <div>
              <div className="flex gap-2">
                <Input
                  type="tel"
                  placeholder="+1 555 000 0000"
                  value={recipientPhone}
                  onChange={(e) => setRecipientPhone(e.target.value)}
                />
                <Button
                  variant="secondary"
                  onClick={handleSendWhatsApp}
                  disabled={isSendingWhatsApp || !recipientPhone}
                >
                  {isSendingWhatsApp ? "Sending..." : "Send via WhatsApp"}
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
