"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { SaleForm } from "@/components/sales/SaleForm";
import { Card } from "@/components/ui/Card";
import { createSale } from "@/lib/api/sales";
import { listCustomers } from "@/lib/api/customers";
import { ApiError } from "@/lib/api/client";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useSubmissionKey } from "@/lib/idempotency";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CustomerResponse } from "@/types/customer";
import { CreateSaleRequest } from "@/types/sale";

export default function NewSalePage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const submission = useSubmissionKey();
  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listCustomers(token, currentBusinessId)
      .then((page) => setCustomers(page.items))
      .catch(() => setCustomers([]));
  }, [currentBusinessId, getAccessToken]);

  async function handleSubmit(data: CreateSaleRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const sale = await createSale(token, currentBusinessId, data, { idempotencyKey: submission.key() });
      router.push(`/app/sales/${sale.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : "Failed to record sale");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New sale</h1>
      <Card className="max-w-2xl">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <SaleForm customers={customers} onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </Card>
    </div>
  );
}
