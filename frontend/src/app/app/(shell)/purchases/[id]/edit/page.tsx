"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PurchaseForm } from "@/components/purchases/PurchaseForm";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getPurchase, updatePurchase } from "@/lib/api/purchases";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { listProducts } from "@/lib/api/products";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ProductResponse } from "@/types/product";
import { CreatePurchaseRequest } from "@/types/purchase";
import { VendorResponse } from "@/types/vendor";

export default function EditPurchasePage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const [vendors, setVendors] = useState<VendorResponse[]>([]);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [initialValues, setInitialValues] = useState<CreatePurchaseRequest | null>(null);
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
    getPurchase(token, currentBusinessId, id)
      .then((purchase) =>
        setInitialValues({
          purchase_number: purchase.purchase_number,
          vendor_id: purchase.vendor_id,
          purchase_date: purchase.purchase_date,
          due_date: purchase.due_date ?? undefined,
          line_items: purchase.line_items.map((item) => ({
            line_number: item.line_number,
            description: item.description,
            quantity: item.quantity,
            unit_cost: item.unit_cost,
            product_id: item.product_id ?? undefined,
          })),
          tax: purchase.tax,
          notes: purchase.notes ?? undefined,
        })
      )
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load purchase"));
  }, [currentBusinessId, getAccessToken, id]);

  async function handleSubmit(data: CreatePurchaseRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      await updatePurchase(token, currentBusinessId, id, data);
      router.push(`/app/purchases/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Edit purchase</h1>
      <Card className="max-w-2xl">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        {initialValues ? (
          <PurchaseForm
            vendors={vendors}
            products={products}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            initialValues={initialValues}
            submitLabel="Save changes"
          />
        ) : (
          !error && (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          )
        )}
      </Card>
    </div>
  );
}
