"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { scanReceipt } from "@/lib/api/expenses";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { createProduct, listProducts } from "@/lib/api/products";
import { createPurchase } from "@/lib/api/purchases";
import { useSubmissionKey } from "@/lib/idempotency";
import { formatCurrency } from "@/lib/format";
import { ProductResponse } from "@/types/product";
import { PurchaseResponse } from "@/types/purchase";
import { VendorResponse } from "@/types/vendor";
import { useT } from "@/lib/i18n/LanguageProvider";

interface Row {
  key: number;
  description: string;
  quantity: string;
  unitCost: string;
  // Where this row's count goes in stock: "" = nowhere, "new" = a new product, else a product id.
  stock: string;
  newSku: string;
  newPrice: string;
}

const NEW_PRODUCT = "new";
const blankStock = { stock: "", newSku: "", newPrice: "" };

const decimalPlaces = (value: string): number => (value.split(".")[1] ?? "").length;

function suggestSku(description: string): string {
  const slug = description.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 20);
  return `${slug || "ITEM"}-${Math.random().toString(36).slice(2, 5).toUpperCase()}`;
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
 * every confirmed line (description, quantity, unit cost). Optionally the counts are also
 * added to stock: each line is matched to a product (or a new product is created) and the
 * server adds the counts in the same transaction as the purchase.
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
  const { t } = useT();
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
  const [addToStock, setAddToStock] = useState(false);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  // Products created for "new" rows, remembered so a retry after a failure doesn't create them twice.
  const createdProducts = useRef<Record<number, string>>({});
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
    listProducts(token, businessId, { limit: 200 })
      .then((page) => setProducts(page.items.filter((p) => p.status !== "inactive")))
      .catch(() => setProducts([]));
  }, [token, businessId]);

  // Turning stock on suggests a product for rows whose name or SKU matches one exactly, and a NEW
  // product (SKU suggested, selling price starting at the cost) for every other row. Ticking the box
  // is a request to add stock, so it must not leave every row on "don't add"; the user can still set
  // any row, such as a delivery fee, back to "Don't add to stock".
  function toggleStock(on: boolean) {
    setAddToStock(on);
    if (!on) return;
    setRows((current) =>
      current.map((row) => {
        if (row.stock) return row;
        const wanted = row.description.trim().toLowerCase();
        const match = products.find((p) => p.name.trim().toLowerCase() === wanted || p.sku.toLowerCase() === wanted);
        if (match) return { ...row, stock: match.id };
        if (row.description.trim() === "") return row;
        return {
          ...row,
          stock: NEW_PRODUCT,
          newSku: row.newSku || suggestSku(row.description),
          newPrice: row.newPrice || row.unitCost,
        };
      })
    );
  }

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
      setNotes(t("scan.from", { file: file.name }));
      const newRows: Row[] =
        found.length > 0
          ? found.map((item) => ({
              key: nextKey.current++,
              description: item.description,
              quantity: item.quantity,
              unitCost: item.unit_price,
              ...blankStock,
            }))
          : scan.amount
            ? [
                {
                  key: nextKey.current++,
                  description: scan.description_guess ?? t("scan.billTotal"),
                  quantity: "1",
                  unitCost: String(Math.max(0, Number(scan.amount) - Number(taxValue || 0)).toFixed(2)),
                  ...blankStock,
                },
              ]
            : [];
      setRows(newRows);
      setStep("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.could_not_read_that_file"));
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
  const stockRows = addToStock ? validRows.filter((r) => r.stock) : [];
  const stockProblem = stockRows.some(
    (r) =>
      decimalPlaces(r.quantity) > 4 ||
      (r.stock === NEW_PRODUCT && (!r.newSku.trim() || cents(r.newPrice) === null || (cents(r.newPrice) ?? 0) < 0))
  );
  // Ticked "add to stock" but every item is set to "Don't add": confirming would silently add nothing.
  const nothingToStock = addToStock && stockRows.length === 0;
  const canConfirm = Boolean(
    typedVendor && billNumber.trim() && validRows.length > 0 && !hasInvalidRow && !stockProblem && !nothingToStock
  );

  function updateRow(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  async function handleConfirm() {
    setError(null);
    setStep("saving");
    try {
      // 1) Create any brand-new products (zero stock; the purchase adds the count). Remembered per
      //    row so a retry after a failed save reuses them instead of creating duplicates.
      const productFor: Record<number, string> = {};
      for (const row of stockRows) {
        if (row.stock !== NEW_PRODUCT) {
          productFor[row.key] = row.stock;
          continue;
        }
        let productId = createdProducts.current[row.key];
        if (!productId) {
          const created = await createProduct(
            token,
            businessId,
            {
              name: row.description.trim(),
              sku: row.newSku.trim(),
              selling_price: row.newPrice,
              purchase_cost: row.unitCost,
              current_quantity: "0",
            },
            { idempotencyKey: `${submission.key()}-product-${row.key}` }
          );
          productId = created.id;
          createdProducts.current[row.key] = productId;
        }
        productFor[row.key] = productId;
      }

      // 2) One purchase with every confirmed line; the server adds the counts to stock atomically.
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
            product_id: productFor[r.key],
          })),
          tax: tax.trim() === "" ? undefined : tax,
          notes: notes.trim() || undefined,
          add_to_stock: stockRows.length > 0 ? true : undefined,
        },
        { idempotencyKey: submission.key() }
      );
      onCreated(purchase);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : t("s.could_not_save_the_purchase"));
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
              {t("s.scan_a_bill")}
            </h2>
            <p className="text-sm text-slate-500">
              {t("s.check_the_items_and_counts_below_n")}
            </p>
          </div>
          <Button variant="ghost" onClick={onClose} disabled={busy} aria-label={t("s.close")}>
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
                ? t("scan.reading")
                : t("scan.choose")}
            </span>
            <span className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700">
              {step === "scanning" ? t("s.please_wait") : t("exp.chooseFile")}
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
                <span className="mb-1 block font-medium">{t("s.vendor_name")}</span>
                <Input
                  required
                  list="scan-bill-vendors"
                  maxLength={200}
                  placeholder={t("s.type_who_this_bill_is_from")}
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
                    {t("scan.seemsToSay", { name: scannedVendor })}
                  </button>
                )}
                {savedVendor && (
                  <span className="mt-1 block text-xs text-slate-500">{t("s.linked_to_your_saved_vendor")}</span>
                )}
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">{t("s.bill_invoice_number")}</span>
                <Input value={billNumber} maxLength={100} onChange={(e) => setBillNumber(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">{t("s.bill_date")}</span>
                <Input type="date" value={billDate} onChange={(e) => setBillDate(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">{t("s.tax_optional")}</span>
                <Input inputMode="decimal" value={tax} onChange={(e) => setTax(e.target.value)} />
              </label>
            </div>

            {!itemsFound && (
              <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                {t("s.no_individual_items_could_be_read")}
              </p>
            )}

            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">{t("s.item")}</th>
                    <th className="w-24 px-3 py-2">{t("s.count")}</th>
                    <th className="w-32 px-3 py-2">{t("s.unit_cost")}</th>
                    <th className="w-28 px-3 py-2 text-right">{t("sale.lineTotal")}</th>
                    {addToStock && <th className="w-56 px-3 py-2">{t("s.add_count_to_stock")}</th>}
                    <th className="w-10 px-3 py-2">
                      <span className="sr-only">{t("set.team.remove")}</span>
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
                            aria-label={t("s.item_description")}
                            value={row.description}
                            onChange={(e) => updateRow(row.key, { description: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            aria-label={t("s.count")}
                            inputMode="decimal"
                            value={row.quantity}
                            onChange={(e) => updateRow(row.key, { quantity: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            aria-label={t("s.unit_cost")}
                            inputMode="decimal"
                            value={row.unitCost}
                            onChange={(e) => updateRow(row.key, { unitCost: e.target.value })}
                          />
                        </td>
                        {addToStock && (
                          <td className="space-y-1 px-3 py-2">
                            <select
                              aria-label={t("scan.stockFor", { item: row.description || t("scan.item") })}
                              value={row.stock}
                              onChange={(e) =>
                                updateRow(row.key, {
                                  stock: e.target.value,
                                  newSku: e.target.value === NEW_PRODUCT ? row.newSku || suggestSku(row.description) : row.newSku,
                                })
                              }
                              className="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm"
                            >
                              <option value="">{t("s.don_t_add_to_stock")}</option>
                              {products.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.name} ({p.sku}) — {Number(p.current_quantity)} in stock
                                </option>
                              ))}
                              <option value={NEW_PRODUCT}>{t("s.new_product_2")}</option>
                            </select>
                            {row.stock === NEW_PRODUCT && (
                              <div className="grid grid-cols-2 gap-1">
                                <Input
                                  aria-label={t("s.new_product_sku")}
                                  placeholder={t("s.sku")}
                                  value={row.newSku}
                                  onChange={(e) => updateRow(row.key, { newSku: e.target.value })}
                                />
                                <Input
                                  aria-label={t("s.new_product_selling_price")}
                                  placeholder={t("s.selling_price")}
                                  inputMode="decimal"
                                  value={row.newPrice}
                                  onChange={(e) => updateRow(row.key, { newPrice: e.target.value })}
                                />
                              </div>
                            )}
                            {row.stock && decimalPlaces(row.quantity) > 4 && (
                              <span className="block text-xs text-red-600">{t("s.stock_counts_allow_up_to_4_decimal")}</span>
                            )}
                          </td>
                        )}
                        <td className="px-3 py-2 text-right">
                          {total === null ? <span className="text-red-600">{t("s.check")}</span> : formatCurrency(total / 100)}
                        </td>
                        <td className="px-3 py-2">
                          <Button
                            variant="ghost"
                            aria-label={t("scan.removeItem", { item: row.description || t("scan.item") })}
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
                  { key: nextKey.current++, description: "", quantity: "1", unitCost: "", ...blankStock },
                ])
              }
            >
              {t("s.add_an_item")}
            </Button>

            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={addToStock}
                onChange={(e) => toggleStock(e.target.checked)}
              />
              <span>
                {t("s.also_add_these_counts_to_my_stock")}
                <span className="block text-xs text-slate-500">
                  {t("scan.stockHelp")}
                </span>
              </span>
            </label>

            {nothingToStock && (
              <p role="alert" className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                {t("s.you_ticked_add_these_counts_to_my")}
              </p>
            )}

            <div className="space-y-1 rounded-md bg-slate-50 p-3 text-sm">
              <div className="flex justify-between">
                <span>Items ({validRows.length})</span>
                <span>{formatCurrency(subtotal / 100)}</span>
              </div>
              <div className="flex justify-between">
                <span>{t("sale.tax")}</span>
                <span>{formatCurrency(taxCents / 100)}</span>
              </div>
              <div className="flex justify-between font-semibold">
                <span>{t("s.purchase_total")}</span>
                <span>{formatCurrency(totalCents / 100)}</span>
              </div>
              {scannedTotal !== null && (
                <div className="flex justify-between text-slate-500">
                  <span>{t("s.total_printed_on_the_bill")}</span>
                  <span>{formatCurrency(scannedTotal)}</span>
                </div>
              )}
            </div>
            {(mismatch || notFoundTotals) && scannedTotal !== null && (
              <p role="status" className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                {t("s.the_items_don_t_add_up_to_the_tota")}
              </p>
            )}

            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("s.notes")}</span>
              <Input value={notes} maxLength={2000} onChange={(e) => setNotes(e.target.value)} />
            </label>

            <div className="flex flex-wrap justify-end gap-3">
              <Button variant="secondary" onClick={onClose} disabled={isSaving}>
                {t("common.cancel")}
              </Button>
              <Button onClick={handleConfirm} disabled={!canConfirm || isSaving}>
                {isSaving
                  ? t("common.saving")
                  : [
                      validRows.length === 1
                        ? t("scan.confirmOne", { total: formatCurrency(totalCents / 100) })
                        : t("scan.confirm", { n: validRows.length, total: formatCurrency(totalCents / 100) }),
                      stockRows.length > 0 ? t("scan.plusStock", { n: stockRows.length }) : "",
                    ]
                      .join(" ")
                      .trim()}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
