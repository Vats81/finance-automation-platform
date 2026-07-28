"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { CreateCustomerRequest } from "@/types/customer";

export function CustomerForm({
  onSubmit,
  isSubmitting,
  initial,
}: {
  onSubmit: (data: CreateCustomerRequest) => void;
  isSubmitting: boolean;
  initial?: Partial<CreateCustomerRequest>;
}) {
  const [form, setForm] = useState<CreateCustomerRequest>({
    name: initial?.name ?? "",
    phone: initial?.phone ?? "",
    email: initial?.email ?? "",
    gst_number: initial?.gst_number ?? "",
    address: initial?.address ?? { street: "", city: "", state: "", postal_code: "", country: "US" },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormField label="Customer name">
        <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Email">
          <Input
            type="email"
            value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </FormField>
        <FormField label="Phone">
          <Input value={form.phone ?? ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </FormField>
      </div>
      <FormField label="GST number">
        <Input
          value={form.gst_number ?? ""}
          onChange={(e) => setForm({ ...form, gst_number: e.target.value })}
        />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <FormField label="Street">
            <Input
              value={form.address?.street ?? ""}
              onChange={(e) =>
                setForm({ ...form, address: { ...form.address!, street: e.target.value } })
              }
            />
          </FormField>
        </div>
        <FormField label="City">
          <Input
            value={form.address?.city ?? ""}
            onChange={(e) => setForm({ ...form, address: { ...form.address!, city: e.target.value } })}
          />
        </FormField>
        <FormField label="State">
          <Input
            value={form.address?.state ?? ""}
            onChange={(e) => setForm({ ...form, address: { ...form.address!, state: e.target.value } })}
          />
        </FormField>
        <FormField label="Postal code">
          <Input
            value={form.address?.postal_code ?? ""}
            onChange={(e) =>
              setForm({ ...form, address: { ...form.address!, postal_code: e.target.value } })
            }
          />
        </FormField>
      </div>
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Saving…" : "Save customer"}
      </Button>
    </form>
  );
}
