"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useT } from "@/lib/i18n/LanguageProvider";
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
  const { t } = useT();
  const { currentBusiness } = useCurrentBusiness();
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<CreateCustomerRequest>({
    name: initial?.name ?? "",
    phone: initial?.phone ?? "",
    email: initial?.email ?? "",
    gst_number: initial?.gst_number ?? "",
    address: initial?.address ?? { street: "", city: "", state: "", postal_code: "", country: "US" },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const clean = (value: string | undefined) => value?.trim() || undefined;
    const a = form.address;
    const parts = a ? [a.street, a.city, a.state, a.postal_code].map((v) => v.trim()) : [];
    const filled = parts.filter(Boolean).length;
    const [street = "", city = "", state = "", postalCode = ""] = parts;
    // The server needs the whole address or none of it, and refuses an empty email, so blanks are left out.
    if (filled > 0 && filled < 4) {
      setFormError(t("cust.addressIncomplete"));
      return;
    }
    setFormError(null);
    onSubmit({
      name: form.name.trim(),
      phone: clean(form.phone),
      email: clean(form.email),
      gst_number: clean(form.gst_number),
      address:
        filled === 4 && a
          ? {
              street,
              city,
              state,
              postal_code: postalCode,
              country: currentBusiness?.business.currency === "INR" ? "IN" : a.country,
            }
          : undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormField label={t("cust.name")}>
        <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <FormField label={t("common.email")}>
          <Input
            type="email"
            value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </FormField>
        <FormField label={t("common.phone")}>
          <Input value={form.phone ?? ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </FormField>
      </div>
      <FormField label={t("cust.gst")}>
        <Input
          value={form.gst_number ?? ""}
          onChange={(e) => setForm({ ...form, gst_number: e.target.value })}
        />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <FormField label={t("cust.street")}>
            <Input
              value={form.address?.street ?? ""}
              onChange={(e) =>
                setForm({ ...form, address: { ...form.address!, street: e.target.value } })
              }
            />
          </FormField>
        </div>
        <FormField label={t("cust.city")}>
          <Input
            value={form.address?.city ?? ""}
            onChange={(e) => setForm({ ...form, address: { ...form.address!, city: e.target.value } })}
          />
        </FormField>
        <FormField label={t("cust.state")}>
          <Input
            value={form.address?.state ?? ""}
            onChange={(e) => setForm({ ...form, address: { ...form.address!, state: e.target.value } })}
          />
        </FormField>
        <FormField label={t("cust.postal")}>
          <Input
            value={form.address?.postal_code ?? ""}
            onChange={(e) =>
              setForm({ ...form, address: { ...form.address!, postal_code: e.target.value } })
            }
          />
        </FormField>
      </div>
      {formError && <p className="text-sm text-red-600">{formError}</p>}
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? t("common.saving") : t("cust.save")}
      </Button>
    </form>
  );
}
