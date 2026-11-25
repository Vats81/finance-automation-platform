"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { resetPassword } from "@/lib/api/auth";
import { useT } from "@/lib/i18n/LanguageProvider";

function ResetPasswordContent() {
  const { t } = useT();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [newPassword, setNewPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const userId = searchParams.get("uid");
  const token = searchParams.get("token");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!userId || !token) {
      setError(t("x.resetLinkMissing"));
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await resetPassword({ user_id: userId, token, new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.this_reset_link_is_invalid_or_has"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <h1 className="mb-1 text-xl font-semibold">{t("s.choose_a_new_password")}</h1>

      {success ? (
        <div className="mt-4 space-y-4 text-center">
          <p className="text-sm text-slate-600">{t("s.your_password_has_been_reset")}</p>
          <Button className="w-full" onClick={() => router.push("/app/login")}>
            {t("auth.signIn")}
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          <FormField label={t("s.new_password")}>
            <Input
              required
              type="password"
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </FormField>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? t("common.saving") : t("s.save_new_password")}
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-slate-500">
        <Link href="/app/login" className="text-brand-600 underline">
          {t("auth.backToSignIn")}
        </Link>
      </p>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Suspense fallback={<Spinner />}>
        <ResetPasswordContent />
      </Suspense>
    </div>
  );
}
