"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { CreatePurchaseLineItemRequest, CreatePurchaseRequest } from "@/types/purchase";
import { ProductResponse } from "@/types/product";
import { VendorResponse } from "@/types/vendor";

function emptyLine(lineNumber: number): CreatePurchaseLineItemRequest {
  return { line_number: lineNumber, description: "", quantity: "1", unit_cost: "0" };
}

export function PurchaseForm({
  vendors,
  products,
  onSubmit,
  isSubmitting,
}: {
  vendors: VendorResponse[];
  products: ProductResponse[];
  onSubmit: (data: CreatePurchaseRequest) => void;
  isSubmitting: boolean;
}) {
  const [purchaseNumber, setPurchaseNumber] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [vendorId, setVendorId] = useState("");
  const [lines, setLines] = useState<CreatePurchaseLineItemRequest[]>([emptyLine(1)]);
  const [tax, setTax] = useState("0");

  function updateLine(index: number, patch: Partial<CreatePurchaseLineItemRequest>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine(prev.length + 1)]);
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index).map((line, i) => ({ ...line, line_number: i + 1 })));
  }

  const subtotal = lines.reduce(
    (sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_cost || 0),
    0
  );
  const total = subtotal + Number(tax || 0);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      purchase_number: purchaseNumber,
      vendor_id: vendorId,
      purchase_date: purchaseDate,
      line_items: lines,
      tax,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Purchase number">
          <Input required value={purchaseNumber} onChange={(e) => setPurchaseNumber(e.target.value)} />
        </FormField>
        <FormField label="Purchase date">
          <Input
            required
            type="date"
            value={purchaseDate}
            onChange={(e) => setPurchaseDate(e.target.value)}
          />
        </FormField>
      </div>

      <FormField label="Vendor">
        <Select required value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
          <option value="" disabled>
            Select a vendor
          </option>
          {vendors.map((vendor) => (
            <option key={vendor.id} value={vendor.id}>
              {vendor.legal_name}
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
              className="col-span-4"
              value={line.description}
              onChange={(e) => updateLine(index, { description: e.target.value })}
            />
            <Select
              className="col-span-3"
              value={line.product_id ?? ""}
              onChange={(e) => updateLine(index, { product_id: e.target.value || undefined })}
            >
              <option value="">No product link</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </Select>
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
              placeholder="Unit cost"
              className="col-span-2"
              value={line.unit_cost}
              onChange={(e) => updateLine(index, { unit_cost: e.target.value })}
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

      <FormField label="Tax">
        <Input type="number" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} />
      </FormField>

      <div className="flex items-center justify-between border-t border-slate-200 pt-4 text-sm">
        <span className="font-medium">Total</span>
        <span className="font-semibold">${total.toFixed(2)}</span>
      </div>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Saving…" : "Record purchase"}
      </Button>
    </form>
  );
}
