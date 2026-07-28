"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ExpenseForm } from "@/components/expenses/ExpenseForm";
import { Card } from "@/components/ui/Card";
import { createExpense } from "@/lib/api/expenses";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CreateExpenseRequest } from "@/types/expense";
import { VendorResponse } from "@/types/vendor";

export default function NewExpensePage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const [vendors, setVendors] = useState<VendorResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listBusinessVendors(token, currentBusinessId)
      .then((page) => setVendors(page.items))
      .catch(() => setVendors([]));
  }, [currentBusinessId, getAccessToken]);

  async function handleSubmit(data: CreateExpenseRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const expense = await createExpense(token, currentBusinessId, data);
      router.push(`/app/expenses/${expense.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record expense");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New expense</h1>
      <Card className="max-w-lg">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <ExpenseForm
          vendors={vendors}
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
          businessId={currentBusinessId}
        />
      </Card>
    </div>
  );
}
