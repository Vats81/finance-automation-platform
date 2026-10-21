"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { CustomerForm } from "@/components/customers/CustomerForm";
import { Card } from "@/components/ui/Card";
import { createCustomer } from "@/lib/api/customers";
import { ApiError } from "@/lib/api/client";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useSubmissionKey } from "@/lib/idempotency";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CreateCustomerRequest } from "@/types/customer";

export default function NewCustomerPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const submission = useSubmissionKey();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CreateCustomerRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const customer = await createCustomer(token, currentBusinessId, data, { idempotencyKey: submission.key() });
      router.push(`/app/customers/${customer.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : "Failed to create customer");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New customer</h1>
      <Card className="max-w-lg">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <CustomerForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </Card>
    </div>
  );
}
