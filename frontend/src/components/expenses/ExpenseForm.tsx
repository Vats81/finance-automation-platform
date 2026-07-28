"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { scanReceipt } from "@/lib/api/expenses";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { CreateExpenseRequest, PaymentMethod } from "@/types/expense";
import { VendorResponse } from "@/types/vendor";

const PAYMENT_METHODS: PaymentMethod[] = ["cash", "card", "bank_transfer", "upi", "other"];

export function ExpenseForm({
  vendors,
  onSubmit,
  isSubmitting,
  businessId,
}: {
  vendors: VendorResponse[];
  onSubmit: (data: CreateExpenseRequest) => void;
  isSubmitting: boolean;
  businessId: string | null;
}) {
  const { getAccessToken } = useLocalAuth();
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("0");
  const [tax, setTax] = useState("0");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cash");
  const [vendorId, setVendorId] = useState("");
  const [isRecurring, setIsRecurring] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanHint, setScanHint] = useState<string | null>(null);

  async function handleReceiptSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !businessId) return;

    setIsScanning(true);
    setScanHint(null);
    try {
      const result = await scanReceipt(getAccessToken(), businessId, file);
      let sawAnyField = false;
      if (result.category_guess) {
        setCategory(result.category_guess);
        sawAnyField = true;
      }
      if (result.description_guess || result.vendor_name) {
        setDescription(
          result.description_guess ?? `Purchase from ${result.vendor_name}`
        );
        sawAnyField = true;
      }
      if (result.amount) {
        setAmount(result.amount);
        sawAnyField = true;
      }
      if (result.expense_date) {
        setExpenseDate(result.expense_date);
        sawAnyField = true;
      }
      if (!sawAnyField) {
        setScanHint(result.raw_text || "Couldn't read any details — please enter them manually.");
      }
    } catch (err) {
      setScanHint(err instanceof Error ? err.message : "Failed to scan the receipt");
    } finally {
      setIsScanning(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      expense_date: expenseDate,
      category,
      description,
      amount,
      tax,
      payment_method: paymentMethod,
      vendor_id: vendorId || undefined,
      is_recurring: isRecurring,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {businessId && (
        <div className="rounded-md border border-dashed border-slate-300 p-3">
          <label className="flex cursor-pointer items-center justify-between gap-3">
            <span className="text-sm text-slate-600">
              {isScanning ? "Scanning receipt…" : "Scan a receipt to pre-fill this form"}
            </span>
            <span className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200">
              Choose file
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={isScanning}
              onChange={handleReceiptSelected}
            />
          </label>
          {scanHint && <p className="mt-2 text-xs text-slate-500">{scanHint}</p>}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Expense date">
          <Input
            required
            type="date"
            value={expenseDate}
            onChange={(e) => setExpenseDate(e.target.value)}
          />
        </FormField>
        <FormField label="Category">
          <Input
            required
            placeholder="e.g. Utilities, Rent, Supplies"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </FormField>
      </div>

      <FormField label="Description">
        <Input
          required
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </FormField>

      <FormField label="Vendor (optional)">
        <Select value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
          <option value="">No vendor</option>
          {vendors.map((vendor) => (
            <option key={vendor.id} value={vendor.id}>
              {vendor.legal_name}
            </option>
          ))}
        </Select>
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Amount">
          <Input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </FormField>
        <FormField label="Tax">
          <Input type="number" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} />
        </FormField>
      </div>

      <FormField label="Payment method">
        <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}>
          {PAYMENT_METHODS.map((method) => (
            <option key={method} value={method}>
              {method.replace("_", " ")}
            </option>
          ))}
        </Select>
      </FormField>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isRecurring}
          onChange={(e) => setIsRecurring(e.target.checked)}
          className="rounded border-slate-300"
        />
        Recurring expense
      </label>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Saving…" : "Record expense"}
      </Button>
    </form>
  );
}
