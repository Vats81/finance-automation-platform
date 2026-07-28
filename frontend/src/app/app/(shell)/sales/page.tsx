"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { SaleTable } from "@/components/sales/SaleTable";
import { listSales } from "@/lib/api/sales";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { SaleResponse } from "@/types/sale";

export default function SalesPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [sales, setSales] = useState<SaleResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listSales(token, currentBusinessId)
      .then((page) => setSales(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load sales"));
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Sales</h1>
        <Link href="/app/sales/new">
          <Button>New sale</Button>
        </Link>
      </div>

      <Card>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!sales && !error ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <SaleTable sales={sales ?? []} />
        )}
      </Card>
    </div>
  );
}
