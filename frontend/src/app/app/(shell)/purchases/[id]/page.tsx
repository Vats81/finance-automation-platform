"use client";

import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { getPurchase, recordPurchasePayment, voidPurchase } from "@/lib/api/purchases";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { PurchasePaymentStatus, PurchaseResponse } from "@/types/purchase";

const STATUS_TONE: Record<PurchasePaymentStatus, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

export default function PurchaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [purchase, setPurchase] = useState<PurchaseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  const load = useCallback(async () => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    try {
      setPurchase(await getPurchase(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load purchase");
    }
  }, [currentBusinessId, getAccessToken, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRecordPayment(event: FormEvent) {
    event.preventDefault();
    if (!currentBusinessId) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setPurchase(await recordPurchasePayment(token, currentBusinessId, id, paymentAmount));
      setPaymentAmount("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record payment");
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleVoid() {
    if (!currentBusinessId) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setPurchase(await voidPurchase(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to void purchase");
    } finally {
      setIsUpdating(false);
    }
  }

  if (!purchase) {
    return (
      <div className="flex justify-center py-8">
        {error ? <p className="text-sm text-red-600">{error}</p> : <Spinner />}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{purchase.purchase_number}</h1>
          <p className="text-sm text-slate-500">{purchase.purchase_date}</p>
        </div>
        <div className="flex items-center gap-2">
          {purchase.status === "void" && <Badge tone="neutral">void</Badge>}
          <Badge tone={STATUS_TONE[purchase.payment_status]}>
            {purchase.payment_status.replace("_", " ")}
          </Badge>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <Card className="mb-6 max-w-2xl">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-4">Description</th>
              <th className="py-2 pr-4">Qty</th>
              <th className="py-2 pr-4">Unit cost</th>
              <th className="py-2 pr-4">Line total</th>
            </tr>
          </thead>
          <tbody>
            {purchase.line_items.map((item) => (
              <tr key={item.line_number} className="border-b border-slate-100 last:border-0">
                <td className="py-2 pr-4">{item.description}</td>
                <td className="py-2 pr-4">{item.quantity}</td>
                <td className="py-2 pr-4">${item.unit_cost}</td>
                <td className="py-2 pr-4">${item.line_total}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 space-y-1 border-t border-slate-200 pt-4 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Subtotal</span>
            <span>${purchase.subtotal}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Tax</span>
            <span>${purchase.tax}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span>Total</span>
            <span>${purchase.total_amount}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Paid</span>
            <span>${purchase.amount_paid}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span>Outstanding</span>
            <span>${purchase.outstanding_amount}</span>
          </div>
        </div>
      </Card>

      {purchase.status !== "void" && (
        <Card className="max-w-2xl space-y-4">
          {purchase.payment_status !== "paid" && (
            <form onSubmit={handleRecordPayment} className="flex items-end gap-2">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">Record payment</label>
                <Input
                  required
                  type="number"
                  step="0.01"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={isUpdating}>
                Record
              </Button>
            </form>
          )}
          <Button variant="danger" disabled={isUpdating} onClick={handleVoid}>
            Void purchase
          </Button>
        </Card>
      )}
    </div>
  );
}
