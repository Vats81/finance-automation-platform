"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getBusinessVendor } from "@/lib/api/businessVendors";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { VendorResponse, VendorStatus } from "@/types/vendor";

const STATUS_TONE: Record<VendorStatus, "neutral" | "success" | "warning"> = {
  pending_review: "warning",
  active: "success",
  inactive: "neutral",
};

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [vendor, setVendor] = useState<VendorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    getBusinessVendor(token, currentBusinessId, id)
      .then(setVendor)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load vendor"));
  }, [currentBusinessId, getAccessToken, id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!vendor) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{vendor.legal_name}</h1>
        <Badge tone={STATUS_TONE[vendor.status]}>{vendor.status.replace("_", " ")}</Badge>
      </div>

      <Card className="max-w-lg space-y-3 text-sm">
        <div>
          <span className="font-medium text-slate-500">Contact email:</span> {vendor.contact_email}
        </div>
        <div>
          <span className="font-medium text-slate-500">Tax ID:</span> {vendor.tax_id_masked}
        </div>
        <div>
          <span className="font-medium text-slate-500">Address:</span> {vendor.address.street},{" "}
          {vendor.address.city}, {vendor.address.state} {vendor.address.postal_code}
        </div>
      </Card>
    </div>
  );
}
