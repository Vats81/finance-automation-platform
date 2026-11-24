"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { CreateSaleLineItemRequest, CreateSaleRequest } from "@/types/sale";
import { CustomerResponse } from "@/types/customer";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { GST_RATES, GST_STATES, isInterState, normalizeRate, previewGst, stateCodeFromGstin } from "@/lib/gst";

function emptyLine(lineNumber: number): CreateSaleLineItemRequest {
  return { line_number: lineNumber, description: "", quantity: "1", unit_price: "0" };
}

export function SaleForm({
  customers,
  onSubmit,
  isSubmitting,
  initialValues,
  submitLabel,
}: {
  customers: CustomerResponse[];
  onSubmit: (data: CreateSaleRequest) => void;
  isSubmitting: boolean;
  initialValues?: CreateSaleRequest;
  submitLabel?: string;
}) {
  const { currentBusiness } = useCurrentBusiness();
  const business = currentBusiness?.business;
  // GST controls appear for a GST-registered business; everyone else keeps the plain tax amount.
  const gstMode = Boolean(business?.gst_registered);

  const [invoiceNumber, setInvoiceNumber] = useState(initialValues?.invoice_number ?? "");
  const [invoiceDate, setInvoiceDate] = useState(
    initialValues?.invoice_date ?? new Date().toISOString().slice(0, 10)
  );
  const [customerId, setCustomerId] = useState(initialValues?.customer_id ?? "");
  const [lines, setLines] = useState<CreateSaleLineItemRequest[]>(
    (initialValues?.line_items ?? [emptyLine(1)]).map((l) => ({ ...l, gst_rate: normalizeRate(l.gst_rate) }))
  );
  const [discount, setDiscount] = useState(initialValues?.discount ?? "0");
  const [tax, setTax] = useState(initialValues?.tax ?? "0");
  const [placeOfSupply, setPlaceOfSupply] = useState(initialValues?.place_of_supply ?? "");
  const [placeTouched, setPlaceTouched] = useState(Boolean(initialValues?.place_of_supply));

  // The place of supply starts as the customer's state (from their GSTIN) or, failing that, the seller's own.
  const customer = customers.find((c) => c.id === customerId);
  useEffect(() => {
    if (!gstMode || placeTouched) return;
    setPlaceOfSupply(stateCodeFromGstin(customer?.gst_number ?? "") || business?.state_code || "");
  }, [gstMode, placeTouched, customer, business?.state_code]);

  function updateLine(index: number, patch: Partial<CreateSaleLineItemRequest>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine(prev.length + 1)]);
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index).map((line, i) => ({ ...line, line_number: i + 1 })));
  }

  const interState = isInterState(business?.state_code, placeOfSupply);
  const gst = useMemo(
    () => previewGst(lines, Number(discount || 0), interState),
    [lines, discount, interState]
  );

  const subtotal = lines.reduce(
    (sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0),
    0
  );
  const total = gstMode ? gst.totalCents / 100 : subtotal - Number(discount || 0) + Number(tax || 0);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      invoice_number: invoiceNumber,
      invoice_date: invoiceDate,
      customer_id: customerId || undefined,
      line_items: lines.map((l) => ({
        ...l,
        gst_rate: gstMode && l.gst_rate ? l.gst_rate : undefined,
        hsn_code: gstMode && l.hsn_code ? l.hsn_code : undefined,
      })),
      discount,
      tax: gstMode ? undefined : tax,
      place_of_supply: gstMode && placeOfSupply ? placeOfSupply : undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Invoice number">
          <Input required value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />
        </FormField>
        <FormField label="Invoice date">
          <Input
            required
            type="date"
            value={invoiceDate}
            onChange={(e) => setInvoiceDate(e.target.value)}
          />
        </FormField>
      </div>

      <FormField label="Customer (optional)">
        <Select value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
          <option value="">Walk-in / no customer</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name}
            </option>
          ))}
        </Select>
      </FormField>

      {gstMode && (
        <FormField label="Place of supply (the state the goods or service go to)">
          <Select
            value={placeOfSupply}
            onChange={(e) => {
              setPlaceTouched(true);
              setPlaceOfSupply(e.target.value);
            }}
          >
            <option value="">Same as my state</option>
            {GST_STATES.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name} ({s.code})
              </option>
            ))}
          </Select>
        </FormField>
      )}

      <div className="space-y-2">
        <label className="block text-sm font-medium">Line items</label>
        {lines.map((line, index) => (
          <div key={index} className="space-y-1 rounded-md border border-slate-100 p-2 sm:border-0 sm:p-0">
            <div className="grid grid-cols-12 gap-2">
              <Input
                required
                placeholder="Description"
                className="col-span-6"
                value={line.description}
                onChange={(e) => updateLine(index, { description: e.target.value })}
              />
              <Input
                required
                type="number"
                step="any"
                placeholder="Qty"
                className="col-span-2"
                value={line.quantity}
                onChange={(e) => updateLine(index, { quantity: e.target.value })}
              />
              <Input
                required
                type="number"
                step="0.01"
                placeholder="Unit price"
                className="col-span-3"
                value={line.unit_price}
                onChange={(e) => updateLine(index, { unit_price: e.target.value })}
              />
              <button
                type="button"
                onClick={() => removeLine(index)}
                disabled={lines.length === 1}
                className="col-span-1 text-slate-400 hover:text-red-600 disabled:opacity-30"
                aria-label="Remove line"
              >
                ✕
              </button>
            </div>
            {gstMode && (
              <div className="grid grid-cols-12 gap-2">
                <Select
                  aria-label={`GST rate for line ${index + 1}`}
                  className="col-span-6"
                  value={line.gst_rate ?? ""}
                  onChange={(e) => updateLine(index, { gst_rate: e.target.value })}
                >
                  <option value="">No GST</option>
                  {GST_RATES.map((rate) => (
                    <option key={rate} value={rate}>
                      GST {rate}%
                    </option>
                  ))}
                </Select>
                <Input
                  aria-label={`HSN or SAC code for line ${index + 1}`}
                  inputMode="numeric"
                  maxLength={8}
                  placeholder="HSN / SAC (optional)"
                  className="col-span-6"
                  value={line.hsn_code ?? ""}
                  onChange={(e) => updateLine(index, { hsn_code: e.target.value.replace(/\D/g, "") })}
                />
              </div>
            )}
          </div>
        ))}
        <Button type="button" variant="secondary" onClick={addLine}>
          Add line
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Discount">
          <Input type="number" step="0.01" value={discount} onChange={(e) => setDiscount(e.target.value)} />
        </FormField>
        {!gstMode && (
          <FormField label="Tax">
            <Input type="number" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} />
          </FormField>
        )}
      </div>

      {gstMode && gst.groups.some((g) => g.rate > 0) && (
        <div className="rounded-md bg-slate-50 p-3 text-sm">
          <div className="mb-1 font-medium">
            GST {interState ? "(other state: IGST)" : "(within your state: CGST + SGST)"}
          </div>
          {gst.groups
            .filter((g) => g.rate > 0)
            .map((g) => (
              <div key={g.rate} className="flex justify-between text-slate-600">
                <span>
                  {g.rate}% on {formatCurrency(g.taxableCents / 100)}
                </span>
                <span>
                  {interState
                    ? `IGST ${formatCurrency(g.igstCents / 100)}`
                    : `CGST ${formatCurrency(g.cgstCents / 100)} + SGST ${formatCurrency(g.sgstCents / 100)}`}
                </span>
              </div>
            ))}
          <div className="mt-1 flex justify-between border-t border-slate-200 pt-1">
            <span>Total GST</span>
            <span>{formatCurrency(gst.taxCents / 100)}</span>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-slate-200 pt-4 text-sm">
        <span className="font-medium">Total</span>
        <span className="font-semibold">{formatCurrency(total)}</span>
      </div>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Saving…" : submitLabel ?? "Record sale"}
      </Button>
    </form>
  );
}
