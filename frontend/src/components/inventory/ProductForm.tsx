"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { CreateProductRequest } from "@/types/product";

export function ProductForm({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (data: CreateProductRequest) => void;
  isSubmitting: boolean;
}) {
  const [form, setForm] = useState<CreateProductRequest>({
    name: "",
    sku: "",
    selling_price: "0",
    purchase_cost: "0",
    category: "",
    current_quantity: "0",
    minimum_stock_level: "0",
    reorder_quantity: "0",
    unit_of_measurement: "unit",
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Product name">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label="SKU">
          <Input required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
        </FormField>
      </div>

      <FormField label="Category">
        <Input value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })} />
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Selling price">
          <Input
            type="number"
            step="0.01"
            value={form.selling_price}
            onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
          />
        </FormField>
        <FormField label="Purchase cost">
          <Input
            type="number"
            step="0.01"
            value={form.purchase_cost}
            onChange={(e) => setForm({ ...form, purchase_cost: e.target.value })}
          />
        </FormField>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <FormField label="Opening stock">
          <Input
            type="number"
            step="any"
            value={form.current_quantity}
            onChange={(e) => setForm({ ...form, current_quantity: e.target.value })}
          />
        </FormField>
        <FormField label="Minimum stock level">
          <Input
            type="number"
            step="any"
            value={form.minimum_stock_level}
            onChange={(e) => setForm({ ...form, minimum_stock_level: e.target.value })}
          />
        </FormField>
        <FormField label="Reorder quantity">
          <Input
            type="number"
            step="any"
            value={form.reorder_quantity}
            onChange={(e) => setForm({ ...form, reorder_quantity: e.target.value })}
          />
        </FormField>
      </div>

      <FormField label="Unit of measurement">
        <Input
          value={form.unit_of_measurement ?? ""}
          onChange={(e) => setForm({ ...form, unit_of_measurement: e.target.value })}
        />
      </FormField>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Saving…" : "Add product"}
      </Button>
    </form>
  );
}
