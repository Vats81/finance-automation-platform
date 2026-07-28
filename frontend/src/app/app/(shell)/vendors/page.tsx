"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BusinessVendorTable } from "@/components/vendors/BusinessVendorTable";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { VendorResponse } from "@/types/vendor";

export default function VendorsPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [vendors, setVendors] = useState<VendorResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listBusinessVendors(token, currentBusinessId)
      .then((page) => setVendors(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load vendors"));
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Vendors</h1>
        <Link href="/app/vendors/new">
          <Button>New vendor</Button>
        </Link>
      </div>

      <Card>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!vendors && !error ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <BusinessVendorTable vendors={vendors ?? []} />
        )}
      </Card>
    </div>
  );
}
