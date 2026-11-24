"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { registerUser } from "@/lib/api/auth";
import { useT } from "@/lib/i18n/LanguageProvider";

export default function SignupPage() {
  const { t } = useT();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registered, setRegistered] = useState(false);
  const [alreadyVerified, setAlreadyVerified] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const user = await registerUser({ email, password, display_name: displayName });
      setAlreadyVerified(user.is_email_verified);
      setRegistered(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.createFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (registered) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <Card className="w-full max-w-sm text-center">
          <h1 className="mb-2 text-xl font-semibold">
            {alreadyVerified ? t("auth.created") : t("auth.checkEmail")}
          </h1>
          <p className="text-sm text-slate-600">
            {alreadyVerified ? (
              <>
                {t("auth.ready")}{" "}
                <Link href="/app/login" className="text-brand-600 underline">
                  {t("auth.signIn")}
                </Link>{" "}
                {t("auth.toGetStarted")}
              </>
            ) : (
              <>
                {t("auth.sentLink", { email })}{" "}
                <Link href="/app/login" className="text-brand-600 underline">
                  {t("auth.signInLower")}
                </Link>
                {t("auth.stop")}
              </>
            )}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4">
      <div className="mb-3 w-full max-w-sm text-right">
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold">{t("auth.createTitle")}</h1>
        <p className="mb-6 text-sm text-slate-500">{t("auth.tagline")}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          <FormField label={t("auth.fullName")}>
            <Input required value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </FormField>
          <FormField label={t("auth.email")}>
            <Input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
          <FormField label={t("auth.password")}>
            <Input
              required
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </FormField>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? t("auth.creating") : t("auth.createAccount")}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-400">
          {t("auth.agree")}{" "}
          <Link href="/terms" className="underline hover:text-slate-600">
            {t("auth.terms")}
          </Link>{" "}
          {t("auth.and")}{" "}
          <Link href="/privacy" className="underline hover:text-slate-600">
            {t("auth.privacy")}
          </Link>
          {t("auth.agreeTail")}
        </p>

        <p className="mt-4 text-center text-sm text-slate-500">
          {t("auth.haveAccount")}{" "}
          <Link href="/app/login" className="text-brand-600 underline">
            {t("auth.signIn")}
          </Link>
        </p>
      </Card>
    </div>
  );
}
