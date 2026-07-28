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
import { CustomerResponse, CustomerStatus } from "@/types/customer";

const STATUS_TONE: Record<CustomerStatus, "success" | "neutral"> = {
  active: "success",
  inactive: "neutral",
};

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const load = useCallback(async () => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    try {
      setCustomer(await getCustomer(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load customer");
    }
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
      setError(err instanceof Error ? err.message : "Failed to deactivate customer");
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
      setError(err instanceof Error ? err.message : "Failed to reactivate customer");
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
        <Badge tone={STATUS_TONE[customer.status]}>{customer.status}</Badge>
      </div>

      <Card className="max-w-lg space-y-3 text-sm">
        <div>
          <span className="font-medium text-slate-500">Email:</span> {customer.email ?? "—"}
        </div>
        <div>
          <span className="font-medium text-slate-500">Phone:</span> {customer.phone ?? "—"}
        </div>
        <div>
          <span className="font-medium text-slate-500">GST number:</span> {customer.gst_number ?? "—"}
        </div>
        {customer.address && (
          <div>
            <span className="font-medium text-slate-500">Address:</span> {customer.address.street},{" "}
            {customer.address.city}, {customer.address.state} {customer.address.postal_code}
          </div>
        )}

        <div className="pt-2">
          {customer.status === "active" ? (
            <Button variant="danger" disabled={isUpdating} onClick={handleDeactivate}>
              Deactivate
            </Button>
          ) : (
            <Button disabled={isUpdating} onClick={handleReactivate}>
              Reactivate
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
