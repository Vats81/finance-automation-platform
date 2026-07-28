"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { CreateSaleLineItemRequest, CreateSaleRequest } from "@/types/sale";
import { CustomerResponse } from "@/types/customer";

function emptyLine(lineNumber: number): CreateSaleLineItemRequest {
  return { line_number: lineNumber, description: "", quantity: "1", unit_price: "0" };
}

export function SaleForm({
  customers,
  onSubmit,
  isSubmitting,
}: {
  customers: CustomerResponse[];
  onSubmit: (data: CreateSaleRequest) => void;
  isSubmitting: boolean;
}) {
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [customerId, setCustomerId] = useState("");
  const [lines, setLines] = useState<CreateSaleLineItemRequest[]>([emptyLine(1)]);
  const [discount, setDiscount] = useState("0");
  const [tax, setTax] = useState("0");

  function updateLine(index: number, patch: Partial<CreateSaleLineItemRequest>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine(prev.length + 1)]);
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index).map((line, i) => ({ ...line, line_number: i + 1 })));
  }

  const subtotal = lines.reduce(
    (sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0),
    0
  );
  const total = subtotal - Number(discount || 0) + Number(tax || 0);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      invoice_number: invoiceNumber,
      invoice_date: invoiceDate,
      customer_id: customerId || undefined,
      line_items: lines,
      discount,
      tax,
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

      <div className="space-y-2">
        <label className="block text-sm font-medium">Line items</label>
        {lines.map((line, index) => (
          <div key={index} className="grid grid-cols-12 gap-2">
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
        ))}
        <Button type="button" variant="secondary" onClick={addLine}>
          Add line
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Discount">
          <Input type="number" step="0.01" value={discount} onChange={(e) => setDiscount(e.target.value)} />
        </FormField>
        <FormField label="Tax">
          <Input type="number" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} />
        </FormField>
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 pt-4 text-sm">
        <span className="font-medium">Total</span>
        <span className="font-semibold">${total.toFixed(2)}</span>
      </div>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Saving…" : "Record sale"}
      </Button>
    </form>
  );
}
