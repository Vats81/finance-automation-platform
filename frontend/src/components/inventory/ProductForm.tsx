"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { CreateProductRequest } from "@/types/product";
import { useT } from "@/lib/i18n/LanguageProvider";

export function ProductForm({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (data: CreateProductRequest) => void;
  isSubmitting: boolean;
}) {
  const { t } = useT();
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
        <FormField label={t("s.product_name")}>
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label={t("s.sku")}>
          <Input required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
        </FormField>
      </div>

      <FormField label={t("exp.category")}>
        <Input value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })} />
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label={t("s.selling_price")}>
          <Input
            type="number"
            step="0.01"
            value={form.selling_price}
            onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
          />
        </FormField>
        <FormField label={t("s.purchase_cost")}>
          <Input
            type="number"
            step="0.01"
            value={form.purchase_cost}
            onChange={(e) => setForm({ ...form, purchase_cost: e.target.value })}
          />
        </FormField>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <FormField label={t("s.opening_stock")}>
          <Input
            type="number"
            step="any"
            value={form.current_quantity}
            onChange={(e) => setForm({ ...form, current_quantity: e.target.value })}
          />
        </FormField>
        <FormField label={t("s.minimum_stock_level")}>
          <Input
            type="number"
            step="any"
            value={form.minimum_stock_level}
            onChange={(e) => setForm({ ...form, minimum_stock_level: e.target.value })}
          />
        </FormField>
        <FormField label={t("s.reorder_quantity")}>
          <Input
            type="number"
            step="any"
            value={form.reorder_quantity}
            onChange={(e) => setForm({ ...form, reorder_quantity: e.target.value })}
          />
        </FormField>
      </div>

      <FormField label={t("s.unit_of_measurement")}>
        <Input
          value={form.unit_of_measurement ?? ""}
          onChange={(e) => setForm({ ...form, unit_of_measurement: e.target.value })}
        />
      </FormField>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? t("common.saving") : t("s.add_product")}
      </Button>
    </form>
  );
}
