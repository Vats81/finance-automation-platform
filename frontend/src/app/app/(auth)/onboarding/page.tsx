"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { LocalAuthGuard } from "@/components/layout/LocalAuthGuard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { completeOnboarding, registerBusiness } from "@/lib/api/business";
import { createFirm } from "@/lib/api/firms";
import { useSubmissionKey } from "@/lib/idempotency";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { CURRENCY_OPTIONS, detectCurrency } from "@/lib/format";
import { CompleteOnboardingRequest } from "@/types/business";
import { useT } from "@/lib/i18n/LanguageProvider";

function OnboardingContent() {
  const { t } = useT();
  const { getAccessToken } = useLocalAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"choose" | "business" | "firm" | "personal">("choose");
  const [firmName, setFirmName] = useState("");
  const firmSubmission = useSubmissionKey();
  const [step, setStep] = useState<1 | 2>(1);
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [businessName, setBusinessName] = useState("");
  const [details, setDetails] = useState<CompleteOnboardingRequest>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreateBusiness(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const business = await registerBusiness(token, { name: businessName });
      setBusinessId(business.id);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_register_your_business"));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCreateFirm(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await createFirm(getAccessToken(), firmName.trim(), { idempotencyKey: firmSubmission.key() });
      router.push("/app/firm");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_create_your_firm"));
      setIsSubmitting(false);
    }
  }

  async function handleCreatePersonal(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const workspace = await registerBusiness(token, { name: businessName.trim() || "My money", kind: "personal" });
      await completeOnboarding(token, workspace.id, { currency: detectCurrency() });
      router.push("/app/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_set_up_your_personal_fin"));
      setIsSubmitting(false);
    }
  }

  async function finishOnboarding(fields: CompleteOnboardingRequest) {
    if (!businessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      await completeOnboarding(token, businessId, fields);
      router.push("/app/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_save_your_business_detai"));
      setIsSubmitting(false);
    }
  }

  if (mode === "choose") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
        <Card className="w-full max-w-lg">
          <h1 className="mb-1 text-xl font-semibold">{t("s.how_will_you_use_finverlo")}</h1>
          <p className="mb-6 text-sm text-slate-500">{t("s.pick_the_one_that_fits_best_you_ca")}</p>
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setMode("business")}
              className="w-full rounded-md border border-slate-300 p-4 text-left hover:border-brand-500 hover:bg-brand-50"
            >
              <div className="font-medium">{t("s.my_business")}</div>
              <div className="text-sm text-slate-500">
                {t("s.track_sales_expenses_purchases_sto")}
              </div>
            </button>
            <button
              type="button"
              onClick={() => setMode("firm")}
              className="w-full rounded-md border border-slate-300 p-4 text-left hover:border-brand-500 hover:bg-brand-50"
            >
              <div className="font-medium">{t("s.i_run_an_accounting_or_bookkeeping")}</div>
              <div className="text-sm text-slate-500">
                {t("s.manage_several_clients_books_from")}
              </div>
            </button>
            <button
              type="button"
              onClick={() => setMode("personal")}
              className="w-full rounded-md border border-slate-300 p-4 text-left hover:border-brand-500 hover:bg-brand-50"
            >
              <div className="font-medium">{t("s.my_personal_finances")}</div>
              <div className="text-sm text-slate-500">
                {t("s.track_your_income_and_spending_and")}
              </div>
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (mode === "personal") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
        <Card className="w-full max-w-lg">
          <h1 className="mb-1 text-xl font-semibold">{t("s.set_up_your_personal_finances")}</h1>
          <p className="mb-6 text-sm text-slate-500">
            {t("s.give_it_a_name_if_you_like_you_can")}
          </p>
          <form onSubmit={handleCreatePersonal} className="space-y-4">
            {error && <p className="text-sm text-red-600">{error}</p>}
            <FormField label={t("common.name")}>
              <Input
                maxLength={255}
                placeholder={t("s.my_money")}
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
              />
            </FormField>
            <div className="flex gap-3">
              <Button type="button" variant="secondary" onClick={() => setMode("choose")} disabled={isSubmitting}>
                {t("tour.back")}
              </Button>
              <Button type="submit" disabled={isSubmitting} className="flex-1">
                {isSubmitting ? t("s.setting_up") : t("dash.getStarted")}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    );
  }

  if (mode === "firm") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
        <Card className="w-full max-w-lg">
          <h1 className="mb-1 text-xl font-semibold">{t("s.set_up_your_firm")}</h1>
          <p className="mb-6 text-sm text-slate-500">
            {t("s.you_ll_be_the_firm_s_owner_next_yo")}
          </p>
          <form onSubmit={handleCreateFirm} className="space-y-4">
            {error && <p className="text-sm text-red-600">{error}</p>}
            <FormField label={t("s.firm_name")}>
              <Input required maxLength={255} value={firmName} onChange={(e) => setFirmName(e.target.value)} />
            </FormField>
            <div className="flex gap-3">
              <Button type="button" variant="secondary" onClick={() => setMode("choose")} disabled={isSubmitting}>
                {t("tour.back")}
              </Button>
              <Button type="submit" disabled={isSubmitting} className="flex-1">
                {isSubmitting ? t("s.creating") : t("s.create_firm")}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <Card className="w-full max-w-lg">
        {step === 1 ? (
          <>
            <h1 className="mb-1 text-xl font-semibold">{t("s.register_your_business")}</h1>
            <p className="mb-6 text-sm text-slate-500">{t("s.step_1_of_2")}</p>
            <form onSubmit={handleCreateBusiness} className="space-y-4">
              {error && <p className="text-sm text-red-600">{error}</p>}
              <FormField label={t("s.business_name")}>
                <Input
                  required
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                />
              </FormField>
              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? t("s.creating") : t("s.continue")}
              </Button>
            </form>
          </>
        ) : (
          <>
            <h1 className="mb-1 text-xl font-semibold">{t("s.tell_us_about_your_business")}</h1>
            <p className="mb-6 text-sm text-slate-500">
              {t("s.step_2_of_2_every_field_here_is_op")}
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void finishOnboarding({ currency: detectCurrency(), ...details });
              }}
              className="space-y-4"
            >
              {error && <p className="text-sm text-red-600">{error}</p>}
              <FormField label={t("set.businessType")}>
                <Input
                  placeholder={t("s.e_g_retail_services_manufacturing")}
                  value={details.business_type ?? ""}
                  onChange={(e) => setDetails({ ...details, business_type: e.target.value })}
                />
              </FormField>
              <FormField label={t("set.industry")}>
                <Input
                  value={details.industry ?? ""}
                  onChange={(e) => setDetails({ ...details, industry: e.target.value })}
                />
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label={t("set.country")}>
                  <Input
                    value={details.country ?? ""}
                    onChange={(e) => setDetails({ ...details, country: e.target.value })}
                  />
                </FormField>
                <FormField label={t("set.currency")}>
                  <Select
                    value={details.currency ?? detectCurrency()}
                    onChange={(e) => setDetails({ ...details, currency: e.target.value })}
                  >
                    {CURRENCY_OPTIONS.map(({ code, label }) => (
                      <option key={code} value={code}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </FormField>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField label={t("s.financial_year_start_month")}>
                  <Select
                    value={details.financial_year_start_month ?? 1}
                    onChange={(e) =>
                      setDetails({ ...details, financial_year_start_month: Number(e.target.value) })
                    }
                  >
                    {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                      <option key={month} value={month}>
                        {new Date(2000, month - 1).toLocaleString("default", { month: "long" })}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <FormField label={t("set.branches")}>
                  <Input
                    type="number"
                    min={1}
                    value={details.number_of_branches ?? 1}
                    onChange={(e) =>
                      setDetails({ ...details, number_of_branches: Number(e.target.value) })
                    }
                  />
                </FormField>
              </div>
              <FormField label={t("set.whatsapp")}>
                <Input
                  placeholder="+91 98765 43210"
                  value={details.whatsapp_number ?? ""}
                  onChange={(e) => setDetails({ ...details, whatsapp_number: e.target.value })}
                />
              </FormField>
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  disabled={isSubmitting}
                  onClick={() => void finishOnboarding({ currency: detectCurrency() })}
                >
                  {t("s.skip_for_now")}
                </Button>
                <Button type="submit" disabled={isSubmitting} className="flex-1">
                  {isSubmitting ? t("common.saving") : t("tour.finish")}
                </Button>
              </div>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <LocalAuthGuard>
      <OnboardingContent />
    </LocalAuthGuard>
  );
}
