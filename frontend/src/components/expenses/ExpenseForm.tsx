"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { scanReceipt } from "@/lib/api/expenses";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
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
  const { t } = useT();
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
          result.description_guess ?? t("exp.purchaseFrom", { vendor: result.vendor_name ?? "" })
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
        setScanHint(result.raw_text || t("exp.scanNothing"));
      }
    } catch (err) {
      setScanHint(err instanceof Error ? err.message : t("exp.scanFailed"));
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
              {isScanning ? t("exp.scanning") : t("exp.scanPrompt")}
            </span>
            <span className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200">
              {t("exp.chooseFile")}
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              className="hidden"
              disabled={isScanning}
              onChange={handleReceiptSelected}
            />
          </label>
          {scanHint && <p className="mt-2 text-xs text-slate-500">{scanHint}</p>}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <FormField label={t("exp.date")}>
          <Input
            required
            type="date"
            value={expenseDate}
            onChange={(e) => setExpenseDate(e.target.value)}
          />
        </FormField>
        <FormField label={t("exp.category")}>
          <Input
            required
            placeholder={t("exp.categoryHint")}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </FormField>
      </div>

      <FormField label={t("common.description")}>
        <Input
          required
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </FormField>

      <FormField label={t("exp.vendorOptional")}>
        <Select value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
          <option value="">{t("exp.noVendor")}</option>
          {vendors.map((vendor) => (
            <option key={vendor.id} value={vendor.id}>
              {vendor.legal_name}
            </option>
          ))}
        </Select>
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label={t("common.amount")}>
          <Input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </FormField>
        <FormField label={t("sale.tax")}>
          <Input type="number" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} />
        </FormField>
      </div>

      <FormField label={t("exp.method")}>
        <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}>
          {PAYMENT_METHODS.map((method) => (
            <option key={method} value={method}>
              {t(`exp.method.${method}` as MessageKey)}
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
        {t("exp.recurring")}
      </label>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? t("common.saving") : t("exp.record")}
      </Button>
    </form>
  );
}
