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
import { useT } from "@/lib/i18n/LanguageProvider";

const STATUS_TONE: Record<VendorStatus, "neutral" | "success" | "warning"> = {
  pending_review: "warning",
  active: "success",
  inactive: "neutral",
};

export default function VendorDetailPage() {
  const { t, label } = useT();
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
      .catch((err) => setError(err instanceof Error ? err.message : t("s.failed_to_load_vendor")));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken, id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!vendor) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  const nameOnly = vendor.contact_email === "";

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{vendor.legal_name}</h1>
        {nameOnly ? (
          <Badge tone="neutral">{t("s.from_a_purchase")}</Badge>
        ) : (
          <Badge tone={STATUS_TONE[vendor.status]}>{label("vendor.status", vendor.status)}</Badge>
        )}
      </div>

      <Card className="max-w-lg space-y-3 text-sm">
        <div>
          <span className="font-medium text-slate-500">{t("s.contact_email")}</span> {vendor.contact_email || "—"}
        </div>
        <div>
          <span className="font-medium text-slate-500">{t("s.tax_id")}</span> {vendor.tax_id_masked || "—"}
        </div>
        <div>
          <span className="font-medium text-slate-500">{t("s.address")}</span>{" "}
          {vendor.address.street
            ? `${vendor.address.street}, ${vendor.address.city}, ${vendor.address.state} ${vendor.address.postal_code}`
            : "—"}
        </div>
        {nameOnly && (
          <div className="text-xs text-slate-500">
            {t("s.added_automatically_from_a_purchas")}
          </div>
        )}
        <div>
        </div>
      </Card>
    </div>
  );
}
