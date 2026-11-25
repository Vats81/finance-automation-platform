"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useT } from "@/lib/i18n/LanguageProvider";
import { CreateBusinessVendorRequest } from "@/types/vendor";

const EMPTY = { legal_name: "", contact_email: "", tax_id: "", street: "", city: "", state: "", postal_code: "" };

/** A supplier needs only a name; everything else is optional and left out when blank. */
export function BusinessVendorForm({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (data: CreateBusinessVendorRequest) => void;
  isSubmitting: boolean;
}) {
  const { t } = useT();
  const { currentBusiness } = useCurrentBusiness();
  const indian = currentBusiness?.business.currency === "INR";
  const [form, setForm] = useState(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);

  function set(field: keyof typeof EMPTY, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const street = form.street.trim();
    const city = form.city.trim();
    const state = form.state.trim();
    const postalCode = form.postal_code.trim();
    const filled = [street, city, state, postalCode].filter(Boolean).length;
    // The server takes the whole address or none of it.
    if (filled > 0 && filled < 4) {
      setFormError(t("cust.addressIncomplete"));
      return;
    }
    setFormError(null);
    onSubmit({
      legal_name: form.legal_name.trim(),
      contact_email: form.contact_email.trim() || undefined,
      tax_id: form.tax_id.trim() || undefined,
      address:
        filled === 4
          ? { street, city, state, postal_code: postalCode, country: indian ? "IN" : "US" }
          : undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormField label={t("s.vendor_name")}>
        <Input required value={form.legal_name} onChange={(e) => set("legal_name", e.target.value)} />
      </FormField>
      <p className="text-xs text-slate-500">{t("vendor.optional")}</p>
      <FormField label={t("vendor.email")}>
        <Input type="email" value={form.contact_email} onChange={(e) => set("contact_email", e.target.value)} />
      </FormField>
      <FormField label={indian ? t("vendor.taxIn") : t("vendor.taxOther")}>
        <Input
          maxLength={20}
          placeholder={indian ? "27AAPFU0939F1ZV" : "12-3456789"}
          value={form.tax_id}
          onChange={(e) => set("tax_id", e.target.value.toUpperCase())}
        />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <FormField label={t("cust.street")}>
            <Input value={form.street} onChange={(e) => set("street", e.target.value)} />
          </FormField>
        </div>
        <FormField label={t("cust.city")}>
          <Input value={form.city} onChange={(e) => set("city", e.target.value)} />
        </FormField>
        <FormField label={t("cust.state")}>
          <Input value={form.state} onChange={(e) => set("state", e.target.value)} />
        </FormField>
        <FormField label={t("cust.postal")}>
          <Input value={form.postal_code} onChange={(e) => set("postal_code", e.target.value)} />
        </FormField>
      </div>
      {formError && <p className="text-sm text-red-600">{formError}</p>}
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? t("s.creating") : t("s.create_vendor")}
      </Button>
    </form>
  );
}
