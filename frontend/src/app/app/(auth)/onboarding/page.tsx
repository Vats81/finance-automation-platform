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
import { CompleteOnboardingRequest } from "@/types/business";

function OnboardingContent() {
  const { getAccessToken } = useLocalAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"choose" | "business" | "firm">("choose");
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
      setError(err instanceof Error ? err.message : "Failed to register your business");
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
      setError(err instanceof Error ? err.message : "Failed to create your firm");
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
      setError(err instanceof Error ? err.message : "Failed to save your business details");
      setIsSubmitting(false);
    }
  }

  if (mode === "choose") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
        <Card className="w-full max-w-lg">
          <h1 className="mb-1 text-xl font-semibold">How will you use Tallyra?</h1>
          <p className="mb-6 text-sm text-slate-500">Pick the one that fits best. You can add the others later.</p>
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setMode("business")}
              className="w-full rounded-md border border-slate-300 p-4 text-left hover:border-brand-500 hover:bg-brand-50"
            >
              <div className="font-medium">My business</div>
              <div className="text-sm text-slate-500">
                Track sales, expenses, purchases, stock and profit for a business you own or run.
              </div>
            </button>
            <button
              type="button"
              onClick={() => setMode("firm")}
              className="w-full rounded-md border border-slate-300 p-4 text-left hover:border-brand-500 hover:bg-brand-50"
            >
              <div className="font-medium">I run an accounting or bookkeeping firm</div>
              <div className="text-sm text-slate-500">
                Manage several clients&apos; books from one place, with your own staff and roles.
              </div>
            </button>
            <div
              aria-disabled="true"
              className="w-full cursor-not-allowed rounded-md border border-dashed border-slate-200 p-4 text-left opacity-60"
            >
              <div className="font-medium">My personal finances</div>
              <div className="text-sm text-slate-500">Income, spending and budgets for one person. Coming soon.</div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (mode === "firm") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
        <Card className="w-full max-w-lg">
          <h1 className="mb-1 text-xl font-semibold">Set up your firm</h1>
          <p className="mb-6 text-sm text-slate-500">
            You&apos;ll be the firm&apos;s owner. Next you can add your clients and your staff.
          </p>
          <form onSubmit={handleCreateFirm} className="space-y-4">
            {error && <p className="text-sm text-red-600">{error}</p>}
            <FormField label="Firm name">
              <Input required maxLength={255} value={firmName} onChange={(e) => setFirmName(e.target.value)} />
            </FormField>
            <div className="flex gap-3">
              <Button type="button" variant="secondary" onClick={() => setMode("choose")} disabled={isSubmitting}>
                Back
              </Button>
              <Button type="submit" disabled={isSubmitting} className="flex-1">
                {isSubmitting ? "Creating…" : "Create firm"}
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
            <h1 className="mb-1 text-xl font-semibold">Register your business</h1>
            <p className="mb-6 text-sm text-slate-500">Step 1 of 2</p>
            <form onSubmit={handleCreateBusiness} className="space-y-4">
              {error && <p className="text-sm text-red-600">{error}</p>}
              <FormField label="Business name">
                <Input
                  required
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                />
              </FormField>
              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? "Creating…" : "Continue"}
              </Button>
            </form>
          </>
        ) : (
          <>
            <h1 className="mb-1 text-xl font-semibold">Tell us about your business</h1>
            <p className="mb-6 text-sm text-slate-500">
              Step 2 of 2 — every field here is optional, you can fill these in later from Settings.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void finishOnboarding(details);
              }}
              className="space-y-4"
            >
              {error && <p className="text-sm text-red-600">{error}</p>}
              <FormField label="Business type">
                <Input
                  placeholder="e.g. Retail, Services, Manufacturing"
                  value={details.business_type ?? ""}
                  onChange={(e) => setDetails({ ...details, business_type: e.target.value })}
                />
              </FormField>
              <FormField label="Industry">
                <Input
                  value={details.industry ?? ""}
                  onChange={(e) => setDetails({ ...details, industry: e.target.value })}
                />
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Country">
                  <Input
                    value={details.country ?? ""}
                    onChange={(e) => setDetails({ ...details, country: e.target.value })}
                  />
                </FormField>
                <FormField label="Currency">
                  <Select
                    value={details.currency ?? "USD"}
                    onChange={(e) => setDetails({ ...details, currency: e.target.value })}
                  >
                    {["USD", "EUR", "GBP", "INR", "AUD", "CAD"].map((code) => (
                      <option key={code} value={code}>
                        {code}
                      </option>
                    ))}
                  </Select>
                </FormField>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Financial year start month">
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
                <FormField label="Number of branches">
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
              <FormField label="WhatsApp number">
                <Input
                  placeholder="+1 555 000 0000"
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
                  onClick={() => void finishOnboarding({})}
                >
                  Skip for now
                </Button>
                <Button type="submit" disabled={isSubmitting} className="flex-1">
                  {isSubmitting ? "Saving…" : "Finish"}
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
