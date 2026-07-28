"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { createPurchaseOrder, listPurchaseOrders } from "@/lib/api/purchaseOrders";
import { listVendors } from "@/lib/api/vendors";
import { useAuth } from "@/lib/auth/useAuth";
import { PurchaseOrderResponse } from "@/types/purchaseOrder";
import { VendorResponse } from "@/types/vendor";

interface LineItemDraft {
  description: string;
  quantity: string;
  unit_price: string;
}

function emptyLineItem(): LineItemDraft {
  return { description: "", quantity: "1", unit_price: "0.00" };
}

function NewPurchaseOrderForm({
  vendors,
  onCreated,
}: {
  vendors: VendorResponse[];
  onCreated: (po: PurchaseOrderResponse) => void;
}) {
  const { getAccessToken } = useAuth();
  const [vendorId, setVendorId] = useState(vendors[0]?.id ?? "");
  const [lines, setLines] = useState<LineItemDraft[]>([emptyLineItem()]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const po = await createPurchaseOrder(token, {
        vendor_id: vendorId,
        line_items: lines.map((line, index) => ({
          line_number: index + 1,
          description: line.description,
          quantity: line.quantity,
          unit_price: line.unit_price,
        })),
      });
      onCreated(po);
      setLines([emptyLineItem()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create purchase order");
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateLine(index: number, patch: Partial<LineItemDraft>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  return (
    <Card className="mb-6">
      <h2 className="mb-4 text-sm font-semibold text-slate-500">New purchase order</h2>
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Vendor</label>
          <select
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value)}
          >
            <option value="" disabled>
              Select a vendor
            </option>
            {vendors.map((v) => (
              <option key={v.id} value={v.id}>
                {v.legal_name}
              </option>
            ))}
          </select>
        </div>

        {lines.map((line, index) => (
          <div key={index} className="grid grid-cols-12 gap-2">
            <input
              required
              placeholder="Description"
              className="col-span-6 rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={line.description}
              onChange={(e) => updateLine(index, { description: e.target.value })}
            />
            <input
              required
              type="number"
              min="0.0001"
              step="any"
              placeholder="Qty"
              className="col-span-3 rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={line.quantity}
              onChange={(e) => updateLine(index, { quantity: e.target.value })}
            />
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              placeholder="Unit price"
              className="col-span-3 rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={line.unit_price}
              onChange={(e) => updateLine(index, { unit_price: e.target.value })}
            />
          </div>
        ))}

        <div className="flex items-center justify-between">
          <Button type="button" variant="secondary" onClick={() => setLines([...lines, emptyLineItem()])}>
            Add line
          </Button>
          <Button type="submit" disabled={isSubmitting || !vendorId}>
            {isSubmitting ? "Creating…" : "Create purchase order"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function PurchaseOrdersContent() {
  const { getAccessToken } = useAuth();
  const [pos, setPos] = useState<PurchaseOrderResponse[] | null>(null);
  const [vendors, setVendors] = useState<VendorResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    const token = await getAccessToken();
    const [poPage, vendorPage] = await Promise.all([listPurchaseOrders(token), listVendors(token)]);
    setPos(poPage.items);
    setVendors(vendorPage.items);
  }

  useEffect(() => {
    reload().catch((err) => setError(err instanceof Error ? err.message : "Failed to load purchase orders"));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">Purchase Orders</h1>
          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <NewPurchaseOrderForm vendors={vendors} onCreated={(po) => setPos((prev) => [po, ...(prev ?? [])])} />

          <Card>
            {!pos ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : pos.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No purchase orders yet.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2 pr-4">PO #</th>
                    <th className="py-2 pr-4">Lines</th>
                    <th className="py-2 pr-4">Total</th>
                    <th className="py-2 pr-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {pos.map((po) => (
                    <tr key={po.id}>
                      <td className="py-3 pr-4 font-mono">{po.po_number}</td>
                      <td className="py-3 pr-4">{po.line_items.length}</td>
                      <td className="py-3 pr-4">${po.total_amount}</td>
                      <td className="py-3 pr-4">
                        <Badge tone={po.status === "open" ? "success" : "neutral"}>{po.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function PurchaseOrdersPage() {
  return (
    <AuthGuard>
      <PurchaseOrdersContent />
    </AuthGuard>
  );
}
