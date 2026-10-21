"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { BusinessVendorForm } from "@/components/vendors/BusinessVendorForm";
import { Card } from "@/components/ui/Card";
import { createBusinessVendor } from "@/lib/api/businessVendors";
import { ApiError } from "@/lib/api/client";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useSubmissionKey } from "@/lib/idempotency";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CreateVendorRequest } from "@/types/vendor";

export default function NewVendorPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const submission = useSubmissionKey();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CreateVendorRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const vendor = await createBusinessVendor(token, currentBusinessId, data, { idempotencyKey: submission.key() });
      router.push(`/app/vendors/${vendor.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : "Failed to create vendor");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New vendor</h1>
      <Card className="max-w-lg">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <BusinessVendorForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </Card>
    </div>
  );
}
