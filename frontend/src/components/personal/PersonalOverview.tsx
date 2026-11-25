"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { getPersonalSummary } from "@/lib/api/personal";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { BudgetStatus, PersonalSummaryResponse } from "@/types/personal";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";

const STATUS_TONE: Record<BudgetStatus, "success" | "warning" | "danger"> = {
  ok: "success",
  near: "warning",
  over: "danger",
};

const STATUS_LABEL: Record<BudgetStatus, MessageKey> = {
  ok: "budget.ok",
  near: "budget.near",
  over: "budget.over",
};

function monthOptions(locale: string): { value: string; label: string }[] {
  const now = new Date();
  return Array.from({ length: 12 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    return {
      value: `${d.getFullYear()}-${d.getMonth() + 1}`,
      label: d.toLocaleString(locale, { month: "long", year: "numeric" }),
    };
  });
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${tone ?? ""}`}>{value}</div>
    </Card>
  );
}

export function PersonalOverview() {
  const { t, lang } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const options = monthOptions(lang === "hi" ? "hi-IN" : "en-US");
  const [period, setPeriod] = useState(options[0]?.value ?? "");
  const [summary, setSummary] = useState<PersonalSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!currentBusinessId) return;
    const [year = 0, month = 0] = period.split("-").map(Number);
    setSummary(null);
    setError(null);
    getPersonalSummary(getAccessToken(), currentBusinessId, year, month)
      .then(setSummary)
      .catch((err) => setError(errorMessage(err, t("s.failed_to_load_your_summary"))));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, period, getAccessToken]);

  useEffect(load, [load]);

  const isEmpty =
    summary !== null &&
    Number(summary.income) === 0 &&
    Number(summary.spending) === 0 &&
    summary.budgets.length === 0;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("nav.overview")}</h1>
        <div className="w-48">
          <Select aria-label={t("dash.month")} value={period} onChange={(e) => setPeriod(e.target.value)}>
            {options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {error && <InlineError message={error} onRetry={load} />}
      {!summary && !error && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {summary && (
        <div className="space-y-6">
          {isEmpty && (
            <Card>
              <p className="mb-3 text-sm text-slate-600">
                {t("s.nothing_here_yet_add_what_you_earn")}
              </p>
              <div className="flex flex-wrap gap-3">
                <Link href="/app/income">
                  <Button>{t("s.add_income")}</Button>
                </Link>
                <Link href="/app/expenses/new">
                  <Button variant="secondary">{t("s.record_spending")}</Button>
                </Link>
                <Link href="/app/budgets">
                  <Button variant="secondary">{t("s.set_a_budget")}</Button>
                </Link>
              </div>
            </Card>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label={t("nav.income")} value={formatCurrency(summary.income)} />
            <Stat label={t("nav.spending")} value={formatCurrency(summary.spending)} />
            <Stat
              label={t("s.saved")}
              value={formatCurrency(summary.saved)}
              tone={Number(summary.saved) < 0 ? "text-red-600" : "text-emerald-700"}
            />
            <Stat
              label={t("s.savings_rate")}
              value={summary.savings_rate === null ? "—" : `${(Number(summary.savings_rate) * 100).toFixed(1)}%`}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <h2 className="mb-3 text-lg font-semibold">{t("s.where_your_money_went")}</h2>
              {summary.spending_by_category.length === 0 ? (
                <p className="text-sm text-slate-500">{t("s.no_spending_recorded_this_month")}</p>
              ) : (
                <ul className="space-y-3">
                  {summary.spending_by_category.map((c) => (
                    <li key={c.category}>
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">{c.category}</span>
                        <span className="text-slate-600">
                          {formatCurrency(c.amount)} · {(Number(c.share) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="mt-1 h-2 rounded-full bg-slate-100">
                        <div
                          className="h-2 rounded-full bg-brand-500"
                          style={{ width: `${Math.min(100, Number(c.share) * 100)}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold">{t("nav.budgets")}</h2>
                <Link href="/app/budgets" className="text-sm text-brand-700 hover:underline">
                  {t("s.manage")}
                </Link>
              </div>
              {summary.budgets.length === 0 ? (
                <p className="text-sm text-slate-500">
                  {t("s.no_budgets_yet_set_a_monthly_limit")}
                </p>
              ) : (
                <ul className="space-y-3">
                  {summary.budgets.map((b) => (
                    <li key={b.id}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{b.category}</span>
                        <Badge tone={STATUS_TONE[b.status]}>{t(STATUS_LABEL[b.status])}</Badge>
                      </div>
                      <div className="mt-1 h-2 rounded-full bg-slate-100">
                        <div
                          className={`h-2 rounded-full ${
                            b.status === "over" ? "bg-red-500" : b.status === "near" ? "bg-amber-500" : "bg-emerald-500"
                          }`}
                          style={{ width: `${Math.min(100, Number(b.percent_used))}%` }}
                        />
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {t("budget.spentOf", {
                          spent: formatCurrency(b.spent),
                          limit: formatCurrency(b.monthly_limit),
                        })}{" "}
                        ·{" "}
                        {Number(b.remaining) >= 0
                          ? t("budget.left", { amount: formatCurrency(b.remaining) })
                          : t("budget.overBy", { amount: formatCurrency(Math.abs(Number(b.remaining))) })}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
