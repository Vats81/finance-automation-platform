"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import { listIncome, recordIncome, voidIncome } from "@/lib/api/personal";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { useSubmissionKey } from "@/lib/idempotency";
import { IncomeResponse } from "@/types/personal";

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function IncomePage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  const canWrite = currentBusiness?.role !== "viewer";
  const submission = useSubmissionKey();
  const [items, setItems] = useState<IncomeResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [date, setDate] = useState(today());
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("Salary");
  const [amount, setAmount] = useState("");

  const load = useCallback(() => {
    if (!currentBusinessId) return;
    setLoadError(null);
    listIncome(getAccessToken(), currentBusinessId)
      .then((page) => setItems(page.items))
      .catch((err) => setLoadError(errorMessage(err, "Failed to load income")));
  }, [currentBusinessId, getAccessToken]);

  useEffect(load, [load]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setFormError(null);
    try {
      await recordIncome(
        getAccessToken(),
        currentBusinessId,
        { income_date: date, source: source.trim(), category: category.trim(), amount },
        { idempotencyKey: submission.key() }
      );
      submission.renew();
      setSource("");
      setAmount("");
      load();
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setFormError(errorMessage(err, "Failed to add income"));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleVoid(id: string) {
    if (!currentBusinessId || !window.confirm("Remove this income entry? It will stop counting in your totals.")) {
      return;
    }
    try {
      await voidIncome(getAccessToken(), currentBusinessId, id);
      load();
    } catch (err) {
      setLoadError(errorMessage(err, "Failed to remove income"));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Income</h1>

      {canWrite && (
        <Card className="max-w-2xl">
          <h2 className="mb-3 text-lg font-semibold">Add income</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Date">
                <Input type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
              </FormField>
              <FormField label="Amount">
                <Input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </FormField>
              <FormField label="From">
                <Input
                  required
                  maxLength={200}
                  placeholder="e.g. Acme Ltd, side project"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                />
              </FormField>
              <FormField label="Type">
                <Input
                  required
                  maxLength={100}
                  placeholder="e.g. Salary, Freelance, Gift"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </FormField>
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Adding…" : "Add income"}
            </Button>
          </form>
        </Card>
      )}

      <Card>
        {loadError && <InlineError message={loadError} onRetry={load} />}
        {!items && !loadError && (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        )}
        {items && items.length === 0 && <p className="text-sm text-slate-500">No income recorded yet.</p>}
        {items && items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">From</th>
                  <th className="py-2 pr-4">Type</th>
                  <th className="py-2 pr-4">Amount</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-4 text-slate-600">{i.income_date}</td>
                    <td className="py-2 pr-4 font-medium">{i.source}</td>
                    <td className="py-2 pr-4 text-slate-600">{i.category}</td>
                    <td className="py-2 pr-4">
                      {i.status === "void" ? (
                        <span className="text-slate-400 line-through">{formatCurrency(i.amount)}</span>
                      ) : (
                        formatCurrency(i.amount)
                      )}
                    </td>
                    <td className="py-2 text-right">
                      {i.status === "void" ? (
                        <Badge tone="neutral">Removed</Badge>
                      ) : (
                        canWrite && (
                          <Button variant="ghost" onClick={() => void handleVoid(i.id)}>
                            Remove
                          </Button>
                        )
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
