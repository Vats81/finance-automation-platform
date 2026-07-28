"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { CreateVendorRequest } from "@/types/vendor";

export function VendorForm({
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
      <div>
        <label className="mb-1 block text-sm font-medium">Legal name</label>
        <input
          required
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={form.legal_name}
          onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Contact email</label>
        <input
          required
          type="email"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={form.contact_email}
          onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Tax ID (EIN, ##-#######)</label>
        <input
          required
          placeholder="12-3456789"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={form.tax_id}
          onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="mb-1 block text-sm font-medium">Street</label>
          <input
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={form.address.street}
            onChange={(e) => setForm({ ...form, address: { ...form.address, street: e.target.value } })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">City</label>
          <input
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={form.address.city}
            onChange={(e) => setForm({ ...form, address: { ...form.address, city: e.target.value } })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">State</label>
          <input
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={form.address.state}
            onChange={(e) => setForm({ ...form, address: { ...form.address, state: e.target.value } })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Postal code</label>
          <input
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={form.address.postal_code}
            onChange={(e) => setForm({ ...form, address: { ...form.address, postal_code: e.target.value } })}
          />
        </div>
      </div>
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Creating…" : "Create vendor"}
      </Button>
    </form>
  );
}
