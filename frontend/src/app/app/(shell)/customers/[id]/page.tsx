"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { deactivateCustomer, getCustomer, reactivateCustomer } from "@/lib/api/customers";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import { CustomerResponse, CustomerStatus } from "@/types/customer";

const STATUS_TONE: Record<CustomerStatus, "success" | "neutral"> = {
  active: "success",
  inactive: "neutral",
};

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const { t } = useT();
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const load = useCallback(async () => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    try {
      setCustomer(await getCustomer(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("cust.loadOneFailed"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDeactivate() {
    if (!currentBusinessId) return;
    setIsUpdating(true);
    try {
      const token = getAccessToken();
      setCustomer(await deactivateCustomer(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("cust.deactivateFailed"));
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleReactivate() {
    if (!currentBusinessId) return;
    setIsUpdating(true);
    try {
      const token = getAccessToken();
      setCustomer(await reactivateCustomer(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("cust.reactivateFailed"));
    } finally {
      setIsUpdating(false);
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!customer) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{customer.name}</h1>
        <Badge tone={STATUS_TONE[customer.status]}>{t(`cust.status.${customer.status}` as MessageKey)}</Badge>
      </div>

      <Card className="max-w-lg space-y-3 text-sm">
        <div>
          <span className="font-medium text-slate-500">{t("common.email")}:</span> {customer.email ?? "—"}
        </div>
        <div>
          <span className="font-medium text-slate-500">{t("common.phone")}:</span> {customer.phone ?? "—"}
        </div>
        <div>
          <span className="font-medium text-slate-500">{t("cust.gst")}:</span> {customer.gst_number ?? "—"}
        </div>
        {customer.address && (
          <div>
            <span className="font-medium text-slate-500">{t("cust.address")}:</span> {customer.address.street},{" "}
            {customer.address.city}, {customer.address.state} {customer.address.postal_code}
          </div>
        )}

        <div className="pt-2">
          {customer.status === "active" ? (
            <Button variant="danger" disabled={isUpdating} onClick={handleDeactivate}>
              {t("cust.deactivate")}
            </Button>
          ) : (
            <Button disabled={isUpdating} onClick={handleReactivate}>
              {t("cust.reactivate")}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
