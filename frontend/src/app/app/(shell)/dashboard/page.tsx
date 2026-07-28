"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RevenueExpenseChart } from "@/components/dashboard/RevenueExpenseChart";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { getInsights } from "@/lib/api/aiAssistant";
import {
  getBusinessHealthScore,
  getDashboardSummary,
  getDashboardTrend,
  getForecast,
} from "@/lib/api/dashboard";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { InsightsResponse } from "@/types/aiAssistant";
import {
  BusinessHealthScoreResponse,
  DASHBOARD_PERIODS,
  DashboardForecastResponse,
  DashboardPeriod,
  DashboardSummaryResponse,
  DashboardTrendResponse,
} from "@/types/dashboard";

const HEALTH_SCORE_TONE: Record<string, "success" | "warning" | "danger"> = {
  Excellent: "success",
  Good: "success",
  Fair: "warning",
  "Needs attention": "danger",
  Critical: "danger",
};

const BREAKDOWN_LABELS: Record<string, string> = {
  profitability: "Profitability",
  revenue_trend: "Revenue trend",
  receivables_health: "Receivables health",
  inventory_health: "Inventory health",
};

function toISODate(d: Date): string {
  // Building from local getters (not toISOString, which converts to UTC
  // and shifts the date by a day in any positive-UTC-offset timezone,
  // e.g. IST) — a period like "this month" must use the viewer's local
  // calendar date, not UTC's.
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getPeriodRange(period: DashboardPeriod): { startDate?: string; endDate?: string } {
  if (period === "all_time") return {};

  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const start =
    period === "this_month"
      ? new Date(year, month, 1)
      : period === "this_quarter"
        ? new Date(year, Math.floor(month / 3) * 3, 1)
        : new Date(year, 0, 1);

  return { startDate: toISODate(start), endDate: toISODate(now) };
}

// The trend chart always needs concrete bounds (a time series needs a
// finite set of buckets), unlike getPeriodRange's summary use, where
// all_time legitimately means "no lower bound". For the chart, all_time is
// deliberately reinterpreted as "last 12 months" — labeled as such in the
// UI so it's a visible simplification, not a silent one.
function getTrendRange(period: DashboardPeriod): { startDate: string; endDate: string } {
  const now = new Date();
  if (period === "all_time") {
    const start = new Date(now.getFullYear(), now.getMonth() - 11, 1);
    return { startDate: toISODate(start), endDate: toISODate(now) };
  }
  const range = getPeriodRange(period);
  return { startDate: range.startDate ?? toISODate(now), endDate: range.endDate ?? toISODate(now) };
}

export default function DashboardPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusiness, currentBusinessId } = useCurrentBusiness();
  const [period, setPeriod] = useState<DashboardPeriod>("this_month");
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [trend, setTrend] = useState<DashboardTrendResponse | null>(null);
  const [healthScore, setHealthScore] = useState<BusinessHealthScoreResponse | null>(null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [isRefreshingInsights, setIsRefreshingInsights] = useState(false);
  const [forecast, setForecast] = useState<DashboardForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    setSummary(null);
    setTrend(null);
    setError(null);
    const token = getAccessToken();
    Promise.all([
      getDashboardSummary(token, currentBusinessId, getPeriodRange(period)),
      getDashboardTrend(token, currentBusinessId, getTrendRange(period)),
    ])
      .then(([summaryRes, trendRes]) => {
        setSummary(summaryRes);
        setTrend(trendRes);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, [currentBusinessId, period, getAccessToken]);

  useEffect(() => {
    // Independent of `period` — the health score is always "as of now",
    // not scoped to the KPI cards' selected period.
    if (!currentBusinessId) return;
    getBusinessHealthScore(getAccessToken(), currentBusinessId)
      .then(setHealthScore)
      .catch(() => undefined);
  }, [currentBusinessId, getAccessToken]);

  useEffect(() => {
    // Independent of `period`, same reasoning as the health score — insights
    // summarize the business "as of now," not a selected date range.
    if (!currentBusinessId) return;
    getInsights(getAccessToken(), currentBusinessId)
      .then(setInsights)
      .catch(() => undefined);
  }, [currentBusinessId, getAccessToken]);

  const handleRefreshInsights = () => {
    if (!currentBusinessId) return;
    setIsRefreshingInsights(true);
    getInsights(getAccessToken(), currentBusinessId)
      .then(setInsights)
      .catch(() => undefined)
      .finally(() => setIsRefreshingInsights(false));
  };

  useEffect(() => {
    // Independent of `period`, same reasoning as Health Score/Insights — a
    // forecast is always "as of now," not scoped to a selected date range.
    if (!currentBusinessId) return;
    getForecast(getAccessToken(), currentBusinessId)
      .then(setForecast)
      .catch(() => undefined);
  }, [currentBusinessId, getAccessToken]);

  const hasTrendActivity = trend?.points.some((p) => Number(p.revenue) !== 0 || Number(p.expenses) !== 0);

  const metrics = [
    { label: "Total revenue", value: summary?.total_revenue, hint: "Connect Sales to see this" },
    { label: "Total expenses", value: summary?.total_expenses, hint: "Connect Expenses to see this" },
    { label: "Net profit", value: summary?.net_profit, hint: "Connect Sales & Expenses to see this" },
    {
      label: "Outstanding receivables",
      value: summary?.outstanding_receivables,
      hint: "Connect Payments to see this",
    },
  ];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-1 text-2xl font-semibold">
            {currentBusiness ? currentBusiness.business.name : "Your business"}
          </h1>
          <p className="text-sm text-slate-500">
            {currentBusiness?.business.onboarding_completed
              ? "Here's an overview of your business."
              : "Finish setting up your business from Settings to unlock more insights."}
          </p>
        </div>
        <div className="w-48">
          <Select value={period} onChange={(e) => setPeriod(e.target.value as DashboardPeriod)}>
            {DASHBOARD_PERIODS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <div className="text-sm font-medium text-slate-500">{metric.label}</div>
            <div className="mt-2 text-2xl font-semibold text-slate-900">
              {metric.value !== undefined ? formatCurrency(metric.value) : "—"}
            </div>
            {metric.value === undefined && <div className="mt-1 text-xs text-slate-400">{metric.hint}</div>}
          </Card>
        ))}
      </div>

      <Card className="mt-6">
        <h2 className="mb-4 text-sm font-semibold">Business Health Score</h2>
        {healthScore ? (
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-bold text-slate-900">{healthScore.overall_score}</span>
              <Badge tone={HEALTH_SCORE_TONE[healthScore.label] ?? "neutral"}>{healthScore.label}</Badge>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
              {Object.entries(healthScore.breakdown).map(([key, value]) => (
                <div key={key}>
                  <span className="text-slate-500">{BREAKDOWN_LABELS[key] ?? key}: </span>
                  {value === null ? (
                    <span className="text-slate-400">Not enough data yet</span>
                  ) : (
                    <span className="font-medium">{Math.round(value * 100)}%</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Loading...</p>
        )}
      </Card>

      <Card className="mt-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold">AI Insights</h2>
          <Button
            variant="secondary"
            onClick={handleRefreshInsights}
            disabled={isRefreshingInsights}
          >
            {isRefreshingInsights ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
        {insights ? (
          <p className="text-sm whitespace-pre-wrap text-slate-700">{insights.insights}</p>
        ) : (
          <p className="text-sm text-slate-500">Loading...</p>
        )}
      </Card>

      <Card className="mt-6">
        <h2 className="mb-4 text-sm font-semibold">
          Revenue vs Expenses{period === "all_time" ? " — Last 12 months" : ""}
        </h2>
        {trend && hasTrendActivity ? (
          <RevenueExpenseChart trend={trend} />
        ) : (
          <p className="text-sm text-slate-500">
            Not enough data yet — import sales or expenses from the{" "}
            <Link href="/app/data-upload" className="text-brand-600 underline">
              Data Upload Centre
            </Link>{" "}
            to see a trend here.
          </p>
        )}
      </Card>

      <Card className="mt-6">
        <h2 className="mb-1 text-sm font-semibold">Forecast</h2>
        {forecast ? (
          <>
            <p className="mb-3 text-xs text-slate-500">
              Projected using trend analysis of your last {forecast.history_months_used} months of data.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-500">
                    <th className="py-2 pr-4 font-medium">Month</th>
                    <th className="py-2 pr-4 font-medium">Projected revenue</th>
                    <th className="py-2 pr-4 font-medium">Projected expenses</th>
                    <th className="py-2 pr-4 font-medium">Projected net profit</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.points.map((point) => (
                    <tr key={point.period_start} className="border-b border-slate-100">
                      <td className="py-2 pr-4">
                        {new Date(point.period_start).toLocaleDateString("en-US", {
                          month: "long",
                          year: "numeric",
                        })}
                      </td>
                      <td className="py-2 pr-4">{formatCurrency(point.projected_revenue)}</td>
                      <td className="py-2 pr-4">{formatCurrency(point.projected_expenses)}</td>
                      <td className="py-2 pr-4">{formatCurrency(point.projected_net_profit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500">Loading...</p>
        )}
      </Card>

      <Card className="mt-6">
        <h2 className="mb-2 text-sm font-semibold">Get started</h2>
        <p className="text-sm text-slate-600">
          Import your sales, expenses, or inventory data from the{" "}
          <Link href="/app/data-upload" className="text-brand-600 underline">
            Data Upload Centre
          </Link>{" "}
          to see these numbers update, or head to{" "}
          <Link href="/app/reports" className="text-brand-600 underline">
            Reports
          </Link>{" "}
          or the{" "}
          <Link href="/app/ai-assistant" className="text-brand-600 underline">
            AI Assistant
          </Link>{" "}
          for a deeper look.
        </p>
      </Card>
    </div>
  );
}
