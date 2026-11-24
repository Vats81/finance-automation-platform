"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiError } from "@/lib/api/client";
import { createCustomer, listCustomers } from "@/lib/api/customers";
import { createSale, getNextInvoiceNumber, recordSalePayment } from "@/lib/api/sales";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { GST_RATES, previewGst } from "@/lib/gst";
import { useSubmissionKey } from "@/lib/idempotency";
import { CustomerResponse } from "@/types/customer";

type Payment = "paid" | "part" | "udhaar";

const PAYMENT_OPTIONS: { value: Payment; label: string }[] = [
  { value: "paid", label: "Paid" },
  { value: "part", label: "Part paid" },
  { value: "udhaar", label: "Udhaar" },
];

const GST_KEY = "finverlo.quickSaleGst";
const NEW_CUSTOMER = "__new__";

/** A sale in a few taps from a phone: an amount, who it was for, and whether they paid. */
export default function QuickSalePage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  const router = useRouter();
  const saleKey = useSubmissionKey();
  const gstMode = Boolean(currentBusiness?.business.gst_registered);

  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [amount, setAmount] = useState("");
  const [item, setItem] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [gstRate, setGstRate] = useState("");
  const [payment, setPayment] = useState<Payment>("paid");
  const [received, setReceived] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // A new customer is made once; a retry after a failed sale must not make them again.
  const createdCustomerId = useRef<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listCustomers(token, currentBusinessId)
      .then((page) => setCustomers(page.items.filter((c) => c.status === "active")))
      .catch(() => setCustomers([]));
    getNextInvoiceNumber(token, currentBusinessId)
      .then(setInvoiceNumber)
      .catch(() => setInvoiceNumber(""));
  }, [currentBusinessId, getAccessToken]);

  useEffect(() => {
    try {
      setGstRate(window.localStorage.getItem(GST_KEY) ?? "");
    } catch {
      // private mode: start from "No GST"
    }
  }, []);

  const total = useMemo(() => {
    const value = Number(amount || 0);
    if (!gstMode) return value;
    return previewGst([{ quantity: "1", unit_price: String(value), gst_rate: gstRate || undefined }], 0, false)
      .totalCents / 100;
  }, [amount, gstMode, gstRate]);

  const isNewCustomer = customerId === NEW_CUSTOMER;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!currentBusinessId) return;
    if (!(Number(amount) > 0)) {
      setError("Enter the amount of the sale.");
      return;
    }
    if (payment === "part" && !(Number(received) > 0 && Number(received) < total)) {
      setError("For a part payment, enter how much was received (less than the total).");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const token = getAccessToken();
      let customer = customerId && !isNewCustomer ? customerId : undefined;
      if (isNewCustomer) {
        if (!newName.trim()) throw new Error("Enter the customer's name.");
        if (!createdCustomerId.current) {
          const created = await createCustomer(token, currentBusinessId, {
            name: newName.trim(),
            phone: newPhone.trim() || undefined,
          });
          createdCustomerId.current = created.id;
        }
        customer = createdCustomerId.current;
      }
      if (payment !== "paid" && !customer) {
        throw new Error("To note who owes you, choose or add the customer.");
      }
      const sale = await createSale(
        token,
        currentBusinessId,
        {
          invoice_number: invoiceNumber || `INV-${Date.now()}`,
          invoice_date: new Date().toISOString().slice(0, 10),
          customer_id: customer,
          line_items: [
            {
              line_number: 1,
              description: item.trim() || "Sale",
              quantity: "1",
              unit_price: amount,
              gst_rate: gstMode && gstRate ? gstRate : undefined,
            },
          ],
        },
        { idempotencyKey: saleKey.key() }
      );
      saleKey.renew();
      try {
        if (payment === "paid") {
          await recordSalePayment(token, currentBusinessId, sale.id, sale.total_amount);
        } else if (payment === "part") {
          await recordSalePayment(token, currentBusinessId, sale.id, received);
        }
      } catch (err) {
        // The sale is saved; only the payment note failed. Say so and let them add it on the sale page.
        router.push(`/app/sales/${sale.id}`);
        console.error("Payment note failed", err);
        return;
      }
      router.push(`/app/sales/${sale.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "duplicate_invoice_number" && currentBusinessId) {
        getNextInvoiceNumber(getAccessToken(), currentBusinessId).then(setInvoiceNumber).catch(() => undefined);
        saleKey.renew();
      }
      setError(err instanceof Error ? err.message : "Could not save the sale");
      setIsSaving(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Quick sale</h1>
      <p className="mb-6 text-sm text-slate-500">
        {invoiceNumber ? `Invoice ${invoiceNumber}` : "Invoice number is made for you"}
      </p>
      <Card className="max-w-md">
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <p className="text-sm text-red-600">{error}</p>}

          <label className="block">
            <span className="mb-1 block text-sm font-medium">Amount</span>
            <Input
              required
              autoFocus
              inputMode="decimal"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              className="text-2xl"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium">What was sold (optional)</span>
            <Input placeholder="Sale" value={item} onChange={(e) => setItem(e.target.value)} />
          </label>

          {gstMode && (
            <label className="block">
              <span className="mb-1 block text-sm font-medium">GST (added on top of the amount)</span>
              <Select
                value={gstRate}
                onChange={(e) => {
                  setGstRate(e.target.value);
                  try {
                    window.localStorage.setItem(GST_KEY, e.target.value);
                  } catch {
                    // ignore: it only remembers the choice
                  }
                }}
              >
                <option value="">No GST</option>
                {GST_RATES.map((rate) => (
                  <option key={rate} value={rate}>
                    GST {rate}%
                  </option>
                ))}
              </Select>
            </label>
          )}

          <label className="block">
            <span className="mb-1 block text-sm font-medium">Customer</span>
            <Select value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
              <option value="">Walk-in (no name)</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
              <option value={NEW_CUSTOMER}>+ New customer</option>
            </Select>
          </label>

          {isNewCustomer && (
            <div className="grid grid-cols-2 gap-3">
              <Input placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} />
              <Input
                placeholder="Phone"
                inputMode="tel"
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
              />
            </div>
          )}

          <div>
            <span className="mb-1 block text-sm font-medium">Payment</span>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Payment">
              {PAYMENT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={payment === option.value}
                  onClick={() => setPayment(option.value)}
                  className={`rounded-md border px-3 py-3 text-sm font-medium ${
                    payment === option.value
                      ? "border-brand-600 bg-brand-50 text-brand-700"
                      : "border-slate-300 bg-white text-slate-700"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {payment === "part" && (
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Received so far</span>
              <Input
                inputMode="decimal"
                type="number"
                step="0.01"
                min="0"
                value={received}
                onChange={(e) => setReceived(e.target.value)}
              />
            </label>
          )}

          <div className="flex items-center justify-between border-t border-slate-200 pt-4 text-sm">
            <span className="font-medium">Total{gstMode && gstRate ? " (with GST)" : ""}</span>
            <span className="text-lg font-semibold">{formatCurrency(total)}</span>
          </div>

          <Button type="submit" disabled={isSaving} className="w-full py-3 text-base">
            {isSaving ? "Saving…" : "Save sale"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
