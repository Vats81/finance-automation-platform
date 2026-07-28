"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { submitInvoice } from "@/lib/api/invoices";
import { listPurchaseOrders } from "@/lib/api/purchaseOrders";
import { useAuth } from "@/lib/auth/useAuth";
import { PurchaseOrderResponse } from "@/types/purchaseOrder";

interface LineItemDraft {
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
}

function NewInvoiceContent() {
  const { getAccessToken } = useAuth();
  const router = useRouter();
  const [pos, setPos] = useState<PurchaseOrderResponse[]>([]);
  const [poId, setPoId] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [lines, setLines] = useState<LineItemDraft[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken()
      .then((token) => listPurchaseOrders(token))
      .then((page) => setPos(page.items.filter((po) => po.status === "open")))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load purchase orders"));
  }, [getAccessToken]);

  function handleSelectPo(id: string) {
    setPoId(id);
    const po = pos.find((p) => p.id === id);
    if (po) {
      setLines(
        po.line_items.map((item) => ({
          line_number: item.line_number,
          description: item.description,
          quantity: item.quantity,
          unit_price: item.unit_price,
        }))
      );
    }
  }

  function updateLine(index: number, patch: Partial<LineItemDraft>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const po = pos.find((p) => p.id === poId);
    if (!po) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const invoice = await submitInvoice(token, {
        invoice_number: invoiceNumber,
        vendor_id: po.vendor_id,
        po_id: po.id,
        line_items: lines,
      });
      router.push(`/invoices/${invoice.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit invoice");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">Submit invoice</h1>
          <Card className="max-w-2xl">
            {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">Invoice number</label>
                <input
                  required
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Purchase order</label>
                <select
                  required
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  value={poId}
                  onChange={(e) => handleSelectPo(e.target.value)}
                >
                  <option value="" disabled>
                    Select an open purchase order
                  </option>
                  {pos.map((po) => (
                    <option key={po.id} value={po.id}>
                      {po.po_number} — ${po.total_amount}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-slate-500">
                  Line items are pre-filled from the PO — edit them to reflect what the paper invoice
                  actually says; a mismatch will surface as a match exception.
                </p>
              </div>

              {lines.length > 0 && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium">Line items</label>
                  {lines.map((line, index) => (
                    <div key={index} className="grid grid-cols-12 gap-2">
                      <input
                        required
                        className="col-span-6 rounded-md border border-slate-300 px-3 py-2 text-sm"
                        value={line.description}
                        onChange={(e) => updateLine(index, { description: e.target.value })}
                      />
                      <input
                        required
                        type="number"
                        step="any"
                        className="col-span-3 rounded-md border border-slate-300 px-3 py-2 text-sm"
                        value={line.quantity}
                        onChange={(e) => updateLine(index, { quantity: e.target.value })}
                      />
                      <input
                        required
                        type="number"
                        step="0.01"
                        className="col-span-3 rounded-md border border-slate-300 px-3 py-2 text-sm"
                        value={line.unit_price}
                        onChange={(e) => updateLine(index, { unit_price: e.target.value })}
                      />
                    </div>
                  ))}
                </div>
              )}

              <Button type="submit" disabled={isSubmitting || !poId} className="w-full">
                {isSubmitting ? "Submitting…" : "Submit invoice"}
              </Button>
            </form>
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function NewInvoicePage() {
  return (
    <AuthGuard>
      <NewInvoiceContent />
    </AuthGuard>
  );
}
