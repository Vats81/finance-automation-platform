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
import { CreateBusinessVendorRequest } from "@/types/vendor";
import { useT } from "@/lib/i18n/LanguageProvider";

export default function NewVendorPage() {
  const { t } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const submission = useSubmissionKey();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CreateBusinessVendorRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const vendor = await createBusinessVendor(token, currentBusinessId, data, { idempotencyKey: submission.key() });
      router.push(`/app/vendors/${vendor.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : t("s.failed_to_create_vendor"));
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">{t("s.new_vendor")}</h1>
      <Card className="max-w-lg">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <BusinessVendorForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </Card>
    </div>
  );
}
