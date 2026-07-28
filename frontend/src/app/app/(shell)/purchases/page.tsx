"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { PurchaseTable } from "@/components/purchases/PurchaseTable";
import { listPurchases } from "@/lib/api/purchases";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { PurchaseResponse } from "@/types/purchase";

export default function PurchasesPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [purchases, setPurchases] = useState<PurchaseResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listPurchases(token, currentBusinessId)
      .then((page) => setPurchases(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load purchases"));
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Purchases</h1>
        <Link href="/app/purchases/new">
          <Button>New purchase</Button>
        </Link>
      </div>

      <Card>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!purchases && !error ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <PurchaseTable purchases={purchases ?? []} />
        )}
      </Card>
    </div>
  );
}
