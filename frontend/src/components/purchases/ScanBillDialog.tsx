"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { scanReceipt } from "@/lib/api/expenses";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { createPurchase } from "@/lib/api/purchases";
import { useSubmissionKey } from "@/lib/idempotency";
import { formatCurrency } from "@/lib/format";
import { PurchaseResponse } from "@/types/purchase";
import { VendorResponse } from "@/types/vendor";

interface Row {
  key: number;
  description: string;
  quantity: string;
  unitCost: string;
}

type Step = "pick" | "scanning" | "review" | "saving";

const cents = (value: string): number | null => {
  if (value.trim() === "" || Number.isNaN(Number(value))) return null;
  return Math.round(Number(value) * 100);
};

function lineCents(row: Row): number | null {
  const qty = Number(row.quantity);
  const cost = cents(row.unitCost);
  if (!(qty > 0) || cost === null || cost < 0) return null;
  return Math.round(qty * cost);
}

const todayISO = () => new Date().toISOString().slice(0, 10);

/**
 * "Scan a bill" -> review -> confirm. The scan only fills this popup in; nothing is saved
 * until the user checks the items and presses Confirm, which records ONE purchase containing
 * every confirmed line (description, quantity, unit cost). It does not change stock counts.
 */
export function ScanBillDialog({
  token,
  businessId,
  onClose,
  onCreated,
}: {
  token: string | null;
  businessId: string;
  onClose: () => void;
  onCreated: (purchase: PurchaseResponse) => void;
}) {
  const [step, setStep] = useState<Step>("pick");
  const [error, setError] = useState<string | null>(null);
  const [vendors, setVendors] = useState<VendorResponse[]>([]);
  const [vendorText, setVendorText] = useState("");
  const [scannedVendor, setScannedVendor] = useState<string | null>(null);
  const [billNumber, setBillNumber] = useState("");
  const [billDate, setBillDate] = useState(todayISO());
  const [tax, setTax] = useState("");
  const [notes, setNotes] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [scannedTotal, setScannedTotal] = useState<string | null>(null);
  const [itemsFound, setItemsFound] = useState(true);
  const [notFoundTotals, setNotFoundTotals] = useState(false);
  const submission = useSubmissionKey();
  const nextKey = useRef(1);
  const dialogRef = useRef<HTMLDivElement>(null);
  const busy = step === "scanning" || step === "saving";

  useEffect(() => {
    listBusinessVendors(token, businessId)
      .then((page) => setVendors(page.items.filter((v) => v.status !== "inactive")))
      .catch(() => setVendors([]));
  }, [token, businessId]);

  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setStep("scanning");
    try {
      const scan = await scanReceipt(token, businessId, file);
      const found = scan.line_items ?? [];
      setItemsFound(found.length > 0);
      const taxValue = scan.tax ?? "";
      setTax(taxValue);
      setBillNumber(scan.invoice_number ?? `SCAN-${todayISO().replace(/-/g, "")}-${Date.now().toString().slice(-4)}`);
      if (scan.expense_date) setBillDate(scan.expense_date);
      setScannedTotal(scan.amount);
      setScannedVendor(scan.vendor_name);
      setNotFoundTotals(scan.totals_match === false);
      setNotes(`Scanned from ${file.name}`);
      const newRows: Row[] =
        found.length > 0
          ? found.map((item) => ({
              key: nextKey.current++,
              description: item.description,
              quantity: item.quantity,
              unitCost: item.unit_price,
            }))
          : scan.amount
            ? [
                {
                  key: nextKey.current++,
                  description: scan.description_guess ?? "Bill total",
                  quantity: "1",
                  unitCost: String(Math.max(0, Number(scan.amount) - Number(taxValue || 0)).toFixed(2)),
                },
              ]
            : [];
      setRows(newRows);
      setStep("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read that file.");
      setStep("pick");
    }
  }

  const validRows = rows.filter((r) => r.description.trim() !== "" && lineCents(r) !== null);
  const subtotal = useMemo(() => validRows.reduce((sum, r) => sum + (lineCents(r) ?? 0), 0), [validRows]);
  const taxCents = cents(tax) ?? 0;
  const totalCents = subtotal + taxCents;
  const hasInvalidRow = rows.some((r) => r.description.trim() === "" || lineCents(r) === null);
  // The vendor is typed by the user. If it matches a saved vendor (ignoring case), the purchase
  // is linked to that vendor; otherwise the typed name is stored on the purchase as-is.
  const typedVendor = vendorText.trim();
  const savedVendor = vendors.find((v) => v.legal_name.trim().toLowerCase() === typedVendor.toLowerCase());
  const mismatch =
    scannedTotal !== null && Math.abs(totalCents - Math.round(Number(scannedTotal) * 100)) > 5;
  const isSaving = step === "saving";
  const canConfirm = Boolean(typedVendor && billNumber.trim() && validRows.length > 0 && !hasInvalidRow);

  function updateRow(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  async function handleConfirm() {
    setError(null);
    setStep("saving");
    try {
      const purchase = await createPurchase(
        token,
        businessId,
        {
          purchase_number: billNumber.trim(),
          vendor_id: savedVendor?.id,
          vendor_name: savedVendor ? undefined : typedVendor,
          purchase_date: billDate,
          line_items: validRows.map((r, index) => ({
            line_number: index + 1,
            description: r.description.trim(),
            quantity: r.quantity,
            unit_cost: r.unitCost,
          })),
          tax: tax.trim() === "" ? undefined : tax,
          notes: notes.trim() || undefined,
        },
        { idempotencyKey: submission.key() }
      );
      onCreated(purchase);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : "Could not save the purchase.");
      setStep("review");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="scan-bill-title"
        tabIndex={-1}
        className="my-8 w-full max-w-3xl rounded-lg bg-white p-6 shadow-xl outline-none"
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id="scan-bill-title" className="text-lg font-semibold">
              Scan a bill
            </h2>
            <p className="text-sm text-slate-500">
              Check the items and counts below. Nothing is saved until you confirm.
            </p>
          </div>
          <Button variant="ghost" onClick={onClose} disabled={busy} aria-label="Close">
            ✕
          </Button>
        </div>

        {error && (
          <p role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        {(step === "pick" || step === "scanning") && (
          <label className="flex cursor-pointer flex-col items-center gap-2 rounded-md border border-dashed border-slate-300 p-8 text-center">
            <span className="text-sm text-slate-600">
              {step === "scanning"
                ? "Reading your bill…"
                : "Choose a photo (JPG, PNG, WebP) or a PDF of the bill, up to 3 MB"}
            </span>
            <span className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700">
              {step === "scanning" ? "Please wait" : "Choose file"}
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              className="hidden"
              disabled={step === "scanning"}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </label>
        )}

        {(step === "review" || step === "saving") && (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="mb-1 block font-medium">Vendor name</span>
                <Input
                  required
                  list="scan-bill-vendors"
                  maxLength={200}
                  placeholder="Type who this bill is from"
                  value={vendorText}
                  onChange={(e) => setVendorText(e.target.value)}
                />
                <datalist id="scan-bill-vendors">
                  {vendors.map((v) => (
                    <option key={v.id} value={v.legal_name} />
                  ))}
                </datalist>
                {scannedVendor && !vendorText && (
                  <button
                    type="button"
                    className="mt-1 text-xs text-brand-700 underline"
                    onClick={() => setVendorText(scannedVendor)}
                  >
                    The bill seems to say &ldquo;{scannedVendor}&rdquo; — use this
                  </button>
                )}
                {savedVendor && (
                  <span className="mt-1 block text-xs text-slate-500">Linked to your saved vendor.</span>
                )}
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">Bill / invoice number</span>
                <Input value={billNumber} maxLength={100} onChange={(e) => setBillNumber(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">Bill date</span>
                <Input type="date" value={billDate} onChange={(e) => setBillDate(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">Tax (optional)</span>
                <Input inputMode="decimal" value={tax} onChange={(e) => setTax(e.target.value)} />
              </label>
            </div>

            {!itemsFound && (
              <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                No individual items could be read from this bill, so it is shown as one line with the bill
                total. You can edit or split it.
              </p>
            )}

            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">Item</th>
                    <th className="w-24 px-3 py-2">Count</th>
                    <th className="w-32 px-3 py-2">Unit cost</th>
                    <th className="w-28 px-3 py-2 text-right">Line total</th>
                    <th className="w-10 px-3 py-2">
                      <span className="sr-only">Remove</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const total = lineCents(row);
                    return (
                      <tr key={row.key} className="border-b border-slate-100 last:border-0">
                        <td className="px-3 py-2">
                          <Input
                            aria-label="Item description"
                            value={row.description}
                            onChange={(e) => updateRow(row.key, { description: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            aria-label="Count"
                            inputMode="decimal"
                            value={row.quantity}
                            onChange={(e) => updateRow(row.key, { quantity: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            aria-label="Unit cost"
                            inputMode="decimal"
                            value={row.unitCost}
                            onChange={(e) => updateRow(row.key, { unitCost: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-2 text-right">
                          {total === null ? <span className="text-red-600">check</span> : formatCurrency(total / 100)}
                        </td>
                        <td className="px-3 py-2">
                          <Button
                            variant="ghost"
                            aria-label={`Remove ${row.description || "item"}`}
                            onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}
                          >
                            ✕
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Button
              variant="secondary"
              onClick={() =>
                setRows((current) => [
                  ...current,
                  { key: nextKey.current++, description: "", quantity: "1", unitCost: "" },
                ])
              }
            >
              Add an item
            </Button>

            <div className="space-y-1 rounded-md bg-slate-50 p-3 text-sm">
              <div className="flex justify-between">
                <span>Items ({validRows.length})</span>
                <span>{formatCurrency(subtotal / 100)}</span>
              </div>
              <div className="flex justify-between">
                <span>Tax</span>
                <span>{formatCurrency(taxCents / 100)}</span>
              </div>
              <div className="flex justify-between font-semibold">
                <span>Purchase total</span>
                <span>{formatCurrency(totalCents / 100)}</span>
              </div>
              {scannedTotal !== null && (
                <div className="flex justify-between text-slate-500">
                  <span>Total printed on the bill</span>
                  <span>{formatCurrency(scannedTotal)}</span>
                </div>
              )}
            </div>
            {(mismatch || notFoundTotals) && scannedTotal !== null && (
              <p role="status" className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                The items don&apos;t add up to the total printed on the bill. A line may have been misread or
                missed — please compare with the original before confirming.
              </p>
            )}

            <label className="block text-sm">
              <span className="mb-1 block font-medium">Notes</span>
              <Input value={notes} maxLength={2000} onChange={(e) => setNotes(e.target.value)} />
            </label>

            <div className="flex flex-wrap justify-end gap-3">
              <Button variant="secondary" onClick={onClose} disabled={isSaving}>
                Cancel
              </Button>
              <Button onClick={handleConfirm} disabled={!canConfirm || isSaving}>
                {isSaving
                  ? "Saving…"
                  : `Confirm — add ${validRows.length} item${validRows.length === 1 ? "" : "s"} (${formatCurrency(totalCents / 100)})`}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
