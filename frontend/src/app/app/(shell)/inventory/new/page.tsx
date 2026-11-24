"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ProductForm } from "@/components/inventory/ProductForm";
import { Card } from "@/components/ui/Card";
import { createProduct } from "@/lib/api/products";
import { ApiError } from "@/lib/api/client";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useSubmissionKey } from "@/lib/idempotency";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CreateProductRequest } from "@/types/product";
import { useT } from "@/lib/i18n/LanguageProvider";

export default function NewProductPage() {
  const { t } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const submission = useSubmissionKey();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CreateProductRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const product = await createProduct(token, currentBusinessId, data, { idempotencyKey: submission.key() });
      router.push(`/app/inventory/${product.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : t("s.failed_to_create_product"));
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">{t("s.new_product")}</h1>
      <Card className="max-w-lg">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <ProductForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </Card>
    </div>
  );
}
