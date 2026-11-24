"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { CustomerTable } from "@/components/customers/CustomerTable";
import { listCustomers } from "@/lib/api/customers";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useT } from "@/lib/i18n/LanguageProvider";
import { CustomerResponse } from "@/types/customer";

export default function CustomersPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const { t } = useT();
  const [customers, setCustomers] = useState<CustomerResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listCustomers(token, currentBusinessId)
      .then((page) => setCustomers(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : t("cust.loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("cust.title")}</h1>
        <Link href="/app/customers/new">
          <Button>{t("cust.new")}</Button>
        </Link>
      </div>

      <Card>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!customers && !error ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <CustomerTable customers={customers ?? []} />
        )}
      </Card>
    </div>
  );
}
