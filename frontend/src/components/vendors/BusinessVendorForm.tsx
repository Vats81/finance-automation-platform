"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { CreateVendorRequest } from "@/types/vendor";

export function BusinessVendorForm({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (data: CreateVendorRequest) => void;
  isSubmitting: boolean;
}) {
  const [form, setForm] = useState<CreateVendorRequest>({
    legal_name: "",
    contact_email: "",
    tax_id: "",
    address: { street: "", city: "", state: "", postal_code: "", country: "US" },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormField label="Legal name">
        <Input
          required
          value={form.legal_name}
          onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
        />
      </FormField>
      <FormField label="Contact email">
        <Input
          required
          type="email"
          value={form.contact_email}
          onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
        />
      </FormField>
      <FormField label="Tax ID (EIN, ##-#######)">
        <Input
          required
          placeholder="12-3456789"
          value={form.tax_id}
          onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
        />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <FormField label="Street">
            <Input
              required
              value={form.address.street}
              onChange={(e) => setForm({ ...form, address: { ...form.address, street: e.target.value } })}
            />
          </FormField>
        </div>
        <FormField label="City">
          <Input
            required
            value={form.address.city}
            onChange={(e) => setForm({ ...form, address: { ...form.address, city: e.target.value } })}
          />
        </FormField>
        <FormField label="State">
          <Input
            required
            value={form.address.state}
            onChange={(e) => setForm({ ...form, address: { ...form.address, state: e.target.value } })}
          />
        </FormField>
        <FormField label="Postal code">
          <Input
            required
            value={form.address.postal_code}
            onChange={(e) =>
              setForm({ ...form, address: { ...form.address, postal_code: e.target.value } })
            }
          />
        </FormField>
      </div>
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Creating…" : "Create vendor"}
      </Button>
    </form>
  );
}
