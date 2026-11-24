"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { requestPasswordReset } from "@/lib/api/auth";
import { useT } from "@/lib/i18n/LanguageProvider";

export default function ForgotPasswordPage() {
  const { t } = useT();
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await requestPasswordReset({ email });
    } finally {
      // Always show the same confirmation, whether or not the email exists —
      // the backend deliberately no-ops for unknown emails to avoid leaking
      // which addresses are registered (see RequestPasswordResetUseCase).
      setIsSubmitting(false);
      setSubmitted(true);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4">
      <div className="mb-3 w-full max-w-sm text-right">
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold">{t("auth.resetTitle")}</h1>
        <p className="mb-6 text-sm text-slate-500">{t("auth.resetText")}</p>

        {submitted ? (
          <p className="text-sm text-slate-600">{t("auth.resetSent", { email })}</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <FormField label={t("auth.email")}>
              <Input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </FormField>
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? t("auth.sending") : t("auth.sendReset")}
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link href="/app/login" className="text-brand-600 underline">
            {t("auth.backToSignIn")}
          </Link>
        </p>
      </Card>
    </div>
  );
}
