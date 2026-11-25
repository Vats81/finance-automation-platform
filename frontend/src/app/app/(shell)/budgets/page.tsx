"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { listBudgets, removeBudget, setBudget } from "@/lib/api/personal";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { BudgetResponse } from "@/types/personal";
import { useT } from "@/lib/i18n/LanguageProvider";

const FREE_BUDGETS = 5; // mirrors backend personal_finance/domain/rules.py

export default function BudgetsPage() {
  const { t } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  const canWrite = currentBusiness?.role !== "viewer";
  const [budgets, setBudgets] = useState<BudgetResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [category, setCategory] = useState("");
  const [limit, setLimit] = useState("");

  const load = useCallback(() => {
    if (!currentBusinessId) return;
    setLoadError(null);
    listBudgets(getAccessToken(), currentBusinessId)
      .then(setBudgets)
      .catch((err) => setLoadError(errorMessage(err, t("s.failed_to_load_budgets"))));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken]);

  useEffect(load, [load]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setFormError(null);
    try {
      await setBudget(getAccessToken(), currentBusinessId, category.trim(), limit);
      setCategory("");
      setLimit("");
      load();
    } catch (err) {
      setFormError(errorMessage(err, t("s.failed_to_save_budget")));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRemove(id: string) {
    if (!currentBusinessId || !window.confirm(t("x.removeBudget"))) return;
    try {
      await removeBudget(getAccessToken(), currentBusinessId, id);
      load();
    } catch (err) {
      setLoadError(errorMessage(err, t("s.failed_to_remove_budget")));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t("nav.budgets")}</h1>
      {currentBusiness?.business.plan === "free" && (
        <p className="text-sm text-slate-500">
          {t("x.freeBudgets", { n: budgets ? budgets.length : "…", max: FREE_BUDGETS })}{" "}
          <Link href="/app/settings" className="text-brand-700 hover:underline">
            {t("s.upgrade_to_plus")}
          </Link>{" "}
          {t("s.for_unlimited")}
        </p>
      )}
      <p className="max-w-2xl text-sm text-slate-600">
        {t("s.a_budget_is_a_monthly_limit_for_on")}
      </p>

      {canWrite && (
        <Card className="max-w-2xl">
          <h2 className="mb-3 text-lg font-semibold">{t("s.set_a_budget")}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label={t("exp.category")}>
                <Input
                  required
                  maxLength={100}
                  placeholder={t("s.e_g_groceries")}
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </FormField>
              <FormField label={t("s.monthly_limit")}>
                <Input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                />
              </FormField>
            </div>
            <p className="text-xs text-slate-500">{t("s.setting_a_category_that_already_ha")}</p>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? t("common.saving") : t("s.save_budget")}
            </Button>
          </form>
        </Card>
      )}

      <Card className="max-w-2xl">
        {loadError && <InlineError message={loadError} onRetry={load} />}
        {!budgets && !loadError && (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        )}
        {budgets && budgets.length === 0 && <p className="text-sm text-slate-500">{t("s.no_budgets_yet")}</p>}
        {budgets && budgets.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {budgets.map((b) => (
              <li key={b.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium">{b.category}</div>
                  <div className="text-sm text-slate-500">{formatCurrency(b.monthly_limit)} per month</div>
                </div>
                {canWrite && (
                  <Button variant="ghost" onClick={() => void handleRemove(b.id)}>
                    {t("set.team.remove")}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
