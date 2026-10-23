"use client";

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

export default function BudgetsPage() {
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
      .catch((err) => setLoadError(errorMessage(err, "Failed to load budgets")));
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
      setFormError(errorMessage(err, "Failed to save budget"));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRemove(id: string) {
    if (!currentBusinessId || !window.confirm("Remove this budget?")) return;
    try {
      await removeBudget(getAccessToken(), currentBusinessId, id);
      load();
    } catch (err) {
      setLoadError(errorMessage(err, "Failed to remove budget"));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Budgets</h1>
      <p className="max-w-2xl text-sm text-slate-600">
        A budget is a monthly limit for one spending category. It matches the category you use when you record
        spending (ignoring capital letters), and your Overview shows how each one is doing.
      </p>

      {canWrite && (
        <Card className="max-w-2xl">
          <h2 className="mb-3 text-lg font-semibold">Set a budget</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Category">
                <Input
                  required
                  maxLength={100}
                  placeholder="e.g. Groceries"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </FormField>
              <FormField label="Monthly limit">
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
            <p className="text-xs text-slate-500">Setting a category that already has a budget updates its limit.</p>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Save budget"}
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
        {budgets && budgets.length === 0 && <p className="text-sm text-slate-500">No budgets yet.</p>}
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
                    Remove
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
