"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PersonalOverview } from "@/components/personal/PersonalOverview";
import { RevenueExpenseChart } from "@/components/dashboard/RevenueExpenseChart";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { MarkdownLite } from "@/components/ui/MarkdownLite";
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
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import { InsightsResponse } from "@/types/aiAssistant";
import {
  BusinessHealthScoreResponse,
  DASHBOARD_PERIODS,
  DashboardForecastResponse,
  DashboardPeriod,
  DashboardSummaryResponse,
  DashboardTrendResponse,
} from "@/types/dashboard";

const PERIOD_KEYS: Record<DashboardPeriod, MessageKey> = {
  this_month: "dash.period.this_month",
  this_quarter: "dash.period.this_quarter",
  this_year: "dash.period.this_year",
  all_time: "dash.period.all_time",
};

const HEALTH_SCORE_TONE: Record<string, "success" | "warning" | "danger"> = {
  Excellent: "success",
  Good: "success",
  Fair: "warning",
  "Needs attention": "danger",
  Critical: "danger",
};

const BREAKDOWN_KEYS: Record<string, MessageKey> = {
  profitability: "dash.breakdown.profitability",
  revenue_trend: "dash.breakdown.revenue_trend",
  receivables_health: "dash.breakdown.receivables_health",
  inventory_health: "dash.breakdown.inventory_health",
};

const LABEL_KEYS: Record<string, MessageKey> = {
  Excellent: "dash.label.Excellent",
  Good: "dash.label.Good",
  Fair: "dash.label.Fair",
  "Needs attention": "dash.label.Needs attention",
  Critical: "dash.label.Critical",
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

function BusinessDashboard() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusiness, currentBusinessId } = useCurrentBusiness();
  const { t, lang } = useT();
  const known = (map: Record<string, MessageKey>, key: string) => {
    const messageKey = map[key];
    return messageKey ? t(messageKey) : key;
  };
  const [period, setPeriod] = useState<DashboardPeriod>("this_month");
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [trend, setTrend] = useState<DashboardTrendResponse | null>(null);
  const [healthScore, setHealthScore] = useState<BusinessHealthScoreResponse | null>(null);
  const [healthScoreError, setHealthScoreError] = useState<string | null>(null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [isRefreshingInsights, setIsRefreshingInsights] = useState(false);
  const [forecast, setForecast] = useState<DashboardForecastResponse | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [healthScoreRetryToken, setHealthScoreRetryToken] = useState(0);
  const [forecastRetryToken, setForecastRetryToken] = useState(0);

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
      .catch((err) => setError(err instanceof Error ? err.message : t("dash.loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, period, getAccessToken]);

  useEffect(() => {
    // Independent of `period` — the health score is always "as of now",
    // not scoped to the KPI cards' selected period.
    if (!currentBusinessId) return;
    setHealthScore(null);
    setHealthScoreError(null);
    getBusinessHealthScore(getAccessToken(), currentBusinessId)
      .then(setHealthScore)
      .catch((err) => setHealthScoreError(errorMessage(err)));
  }, [currentBusinessId, getAccessToken, healthScoreRetryToken]);

  useEffect(() => {
    // Independent of `period`, same reasoning as the health score — insights
    // summarize the business "as of now," not a selected date range.
    if (!currentBusinessId) return;
    getInsights(getAccessToken(), currentBusinessId)
      .then((res) => {
        setInsights(res);
        setInsightsError(null);
      })
      .catch((err) => setInsightsError(errorMessage(err)));
  }, [currentBusinessId, getAccessToken]);

  const handleRefreshInsights = () => {
    if (!currentBusinessId) return;
    setIsRefreshingInsights(true);
    setInsightsError(null);
    getInsights(getAccessToken(), currentBusinessId)
      .then(setInsights)
      .catch((err) => setInsightsError(errorMessage(err)))
      .finally(() => setIsRefreshingInsights(false));
  };

  useEffect(() => {
    // Independent of `period`, same reasoning as Health Score/Insights — a
    // forecast is always "as of now," not scoped to a selected date range.
    if (!currentBusinessId) return;
    setForecast(null);
    setForecastError(null);
    getForecast(getAccessToken(), currentBusinessId)
      .then(setForecast)
      .catch((err) => setForecastError(errorMessage(err)));
  }, [currentBusinessId, getAccessToken, forecastRetryToken]);

  const hasTrendActivity = trend?.points.some((p) => Number(p.revenue) !== 0 || Number(p.expenses) !== 0);

  const metrics = [
    { label: t("dash.revenue"), value: summary?.total_revenue, hint: t("dash.revenueHint") },
    { label: t("dash.expenses"), value: summary?.total_expenses, hint: t("dash.expensesHint") },
    { label: t("dash.profit"), value: summary?.net_profit, hint: t("dash.profitHint") },
    {
      label: t("dash.receivables"),
      value: summary?.outstanding_receivables,
      hint: t("dash.receivablesHint"),
    },
    {
      label: t("dash.purchases"),
      value: summary?.total_purchases,
      hint: t("dash.purchasesHint"),
      note: t("dash.purchasesNote"),
    },
    {
      label: t("dash.payables"),
      value: summary?.outstanding_payables,
      hint: t("dash.purchasesHint"),
      note: t("dash.payablesNote"),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-1 text-2xl font-semibold">
            {currentBusiness ? currentBusiness.business.name : t("dash.yourBusiness")}
          </h1>
          <p className="text-sm text-slate-500">
            {currentBusiness?.business.onboarding_completed
              ? t("dash.overview")
              : t("dash.finishSetup")}
          </p>
        </div>
        <div className="w-48">
          <Select value={period} onChange={(e) => setPeriod(e.target.value as DashboardPeriod)}>
            {DASHBOARD_PERIODS.map((p) => (
              <option key={p.value} value={p.value}>
                {t(PERIOD_KEYS[p.value])}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <div className="text-sm font-medium text-slate-500">{metric.label}</div>
            <div className="mt-2 text-2xl font-semibold text-slate-900">
              {metric.value !== undefined ? formatCurrency(metric.value) : "—"}
            </div>
            {metric.value === undefined && <div className="mt-1 text-xs text-slate-400">{metric.hint}</div>}
            {metric.value !== undefined && "note" in metric && metric.note && (
              <div className="mt-1 text-xs text-slate-400">{metric.note}</div>
            )}
          </Card>
        ))}
      </div>

      <Card className="mt-6">
        <h2 className="mb-4 text-sm font-semibold">{t("dash.health")}</h2>
        {healthScoreError ? (
          <InlineError message={healthScoreError} onRetry={() => setHealthScoreRetryToken((n) => n + 1)} />
        ) : healthScore ? (
          healthScore.overall_score === null ? (
            <p className="text-sm text-slate-500">
              {t("dash.healthNotEnough")}
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-baseline gap-3">
                <span className="text-4xl font-bold text-slate-900">{healthScore.overall_score}</span>
                <Badge tone={HEALTH_SCORE_TONE[healthScore.label] ?? "neutral"}>{known(LABEL_KEYS, healthScore.label)}</Badge>
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
                {Object.entries(healthScore.breakdown).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-slate-500">{known(BREAKDOWN_KEYS, key)}: </span>
                    {value === null ? (
                      <span className="text-slate-400">{t("dash.healthNoData")}</span>
                    ) : (
                      <span className="font-medium">{Math.round(value * 100)}%</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        ) : (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        )}
      </Card>

      <Card className="mt-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold">{t("dash.insights")}</h2>
          <Button
            variant="secondary"
            onClick={handleRefreshInsights}
            disabled={isRefreshingInsights}
          >
            {isRefreshingInsights ? t("dash.refreshing") : t("dash.refresh")}
          </Button>
        </div>
        {insightsError ? (
          <InlineError message={insightsError} onRetry={handleRefreshInsights} />
        ) : insights ? (
          <MarkdownLite text={insights.insights} className="text-sm text-slate-700" />
        ) : (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        )}
      </Card>

      <Card className="mt-6">
        <h2 className="mb-4 text-sm font-semibold">
          {t("dash.trend")}
          {period === "all_time" ? t("dash.trendLast12") : ""}
        </h2>
        {trend && hasTrendActivity ? (
          <RevenueExpenseChart trend={trend} />
        ) : (
          <p className="text-sm text-slate-500">
            {t("dash.noTrend")}{" "}
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

      <Card className="mt-6">
        <h2 className="mb-1 text-sm font-semibold">{t("dash.forecast")}</h2>
        {forecastError ? (
          <InlineError message={forecastError} onRetry={() => setForecastRetryToken((n) => n + 1)} />
        ) : forecast ? (
          forecast.is_available ? (
            <>
              <p className="mb-3 text-xs text-slate-500">
                {t("dash.forecastNote", {
                  months: forecast.history_months_used,
                  active: forecast.months_with_activity,
                })}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-slate-500">
                      <th className="py-2 pr-4 font-medium">{t("dash.month")}</th>
                      <th className="py-2 pr-4 font-medium">{t("dash.projRevenue")}</th>
                      <th className="py-2 pr-4 font-medium">{t("dash.projExpenses")}</th>
                      <th className="py-2 pr-4 font-medium">{t("dash.projProfit")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.points.map((point) => (
                      <tr key={point.period_start} className="border-b border-slate-100">
                        <td className="py-2 pr-4">
                          {new Date(point.period_start).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-US", {
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
            <p className="text-sm text-slate-500">
              {t("dash.forecastNone", {
                months: forecast.history_months_used,
                active: forecast.months_with_activity,
              })}
            </p>
          )
        ) : (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        )}
      </Card>

      <Card className="mt-6">
        <h2 className="mb-2 text-sm font-semibold">{t("dash.getStarted")}</h2>
        <p className="mb-2 text-sm text-slate-600">{t("dash.getStartedText")}</p>
        <ul className="list-inside list-disc space-y-1 text-sm">
          <li>
            <Link href="/app/sales/quick" className="text-brand-600 underline">
              {t("sales.quick")}
            </Link>
          </li>
          <li>
            <Link href="/app/expenses/new" className="text-brand-600 underline">
              {t("dash.recordExpense")}
            </Link>
          </li>
          <li>
            <Link href="/app/data-upload" className="text-brand-600 underline">
              {t("dash.dataUpload")}
            </Link>
          </li>
          <li>
            <Link href="/app/reports" className="text-brand-600 underline">
              {t("nav.reports")}
            </Link>
          </li>
          <li>
            <Link href="/app/ai-assistant" className="text-brand-600 underline">
              {t("nav.aiAssistant")}
            </Link>
          </li>
        </ul>
      </Card>
    </div>
  );
}

export default function DashboardPage() {
  const { currentBusiness } = useCurrentBusiness();
  return currentBusiness?.business.kind === "personal" ? <PersonalOverview /> : <BusinessDashboard />;
}
