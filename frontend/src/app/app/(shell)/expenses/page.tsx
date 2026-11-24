"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ExpenseTable } from "@/components/expenses/ExpenseTable";
import { listExpenses } from "@/lib/api/expenses";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useT } from "@/lib/i18n/LanguageProvider";
import { ExpenseResponse } from "@/types/expense";

export default function ExpensesPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const { t } = useT();
  const [expenses, setExpenses] = useState<ExpenseResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listExpenses(token, currentBusinessId)
      .then((page) => setExpenses(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : t("exp.loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("exp.title")}</h1>
        <Link href="/app/expenses/new">
          <Button>{t("exp.new")}</Button>
        </Link>
      </div>

      <Card>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!expenses && !error ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <ExpenseTable expenses={expenses ?? []} />
        )}
      </Card>
    </div>
  );
}
