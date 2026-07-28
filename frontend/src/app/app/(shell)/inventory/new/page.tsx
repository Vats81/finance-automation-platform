"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ProductForm } from "@/components/inventory/ProductForm";
import { Card } from "@/components/ui/Card";
import { createProduct } from "@/lib/api/products";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CreateProductRequest } from "@/types/product";

export default function NewProductPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CreateProductRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const product = await createProduct(token, currentBusinessId, data);
      router.push(`/app/inventory/${product.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create product");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New product</h1>
      <Card className="max-w-lg">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <ProductForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </Card>
    </div>
  );
}
