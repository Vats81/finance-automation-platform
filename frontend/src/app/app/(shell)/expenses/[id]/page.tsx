"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getExpense, voidExpense } from "@/lib/api/expenses";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ExpenseResponse } from "@/types/expense";

export default function ExpenseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [expense, setExpense] = useState<ExpenseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const load = useCallback(async () => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    try {
      setExpense(await getExpense(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load expense");
    }
  }, [currentBusinessId, getAccessToken, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleVoid() {
    if (!currentBusinessId) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setExpense(await voidExpense(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to void expense");
    } finally {
      setIsUpdating(false);
    }
  }

  if (!expense) {
    return (
      <div className="flex justify-center py-8">
        {error ? <p className="text-sm text-red-600">{error}</p> : <Spinner />}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{expense.category}</h1>
          <p className="text-sm text-slate-500">{expense.expense_date}</p>
        </div>
        {expense.status === "void" && <Badge tone="neutral">void</Badge>}
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <Card className="mb-6 max-w-lg space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Description</span>
          <span>{expense.description}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Amount</span>
          <span>${expense.amount}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Tax</span>
          <span>${expense.tax}</span>
        </div>
        <div className="flex justify-between font-semibold">
          <span>Total</span>
          <span>${expense.total_amount}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Payment method</span>
          <span>{expense.payment_method.replace("_", " ")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Recurring</span>
          <span>{expense.is_recurring ? "Yes" : "No"}</span>
        </div>
      </Card>

      {expense.status !== "void" && (
        <Button variant="danger" disabled={isUpdating} onClick={handleVoid}>
          Void expense
        </Button>
      )}
    </div>
  );
}
