"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PurchaseForm } from "@/components/purchases/PurchaseForm";
import { Card } from "@/components/ui/Card";
import { createPurchase } from "@/lib/api/purchases";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { listProducts } from "@/lib/api/products";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ProductResponse } from "@/types/product";
import { CreatePurchaseRequest } from "@/types/purchase";
import { VendorResponse } from "@/types/vendor";

export default function NewPurchasePage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const [vendors, setVendors] = useState<VendorResponse[]>([]);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listBusinessVendors(token, currentBusinessId)
      .then((page) => setVendors(page.items))
      .catch(() => setVendors([]));
    listProducts(token, currentBusinessId)
      .then((page) => setProducts(page.items))
      .catch(() => setProducts([]));
  }, [currentBusinessId, getAccessToken]);

  async function handleSubmit(data: CreatePurchaseRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const purchase = await createPurchase(token, currentBusinessId, data);
      router.push(`/app/purchases/${purchase.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record purchase");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New purchase</h1>
      <Card className="max-w-2xl">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <PurchaseForm
          vendors={vendors}
          products={products}
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
        />
      </Card>
    </div>
  );
}
