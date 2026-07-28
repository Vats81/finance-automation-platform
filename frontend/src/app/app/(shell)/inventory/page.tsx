"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ProductTable } from "@/components/inventory/ProductTable";
import { listProducts } from "@/lib/api/products";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ProductResponse } from "@/types/product";

export default function InventoryPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [products, setProducts] = useState<ProductResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listProducts(token, currentBusinessId)
      .then((page) => setProducts(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load products"));
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Inventory</h1>
        <Link href="/app/inventory/new">
          <Button>New product</Button>
        </Link>
      </div>

      <Card>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!products && !error ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <ProductTable products={products ?? []} />
        )}
      </Card>
    </div>
  );
}
