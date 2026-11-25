"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { verifyEmail } from "@/lib/api/auth";
import { useT } from "@/lib/i18n/LanguageProvider";

type Status = "verifying" | "success" | "error";

function VerifyEmailContent() {
  const { t } = useT();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<Status>("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const userId = searchParams.get("uid");
    const token = searchParams.get("token");
    if (!userId || !token) {
      setStatus("error");
      setError(t("x.verifyLinkMissing"));
      return;
    }

    verifyEmail({ user_id: userId, token })
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setError(err instanceof Error ? err.message : t("s.this_verification_link_is_invalid"));
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <Card className="w-full max-w-sm text-center">
      {status === "verifying" && (
        <>
          <div className="mb-4 flex justify-center">
            <Spinner />
          </div>
          <p className="text-sm text-slate-600">{t("s.verifying_your_email")}</p>
        </>
      )}
      {status === "success" && (
        <>
          <h1 className="mb-2 text-xl font-semibold">{t("s.email_verified")}</h1>
          <p className="mb-4 text-sm text-slate-600">{t("s.your_account_is_now_active")}</p>
          <Link href="/app/login" className="text-brand-600 underline">
            {t("auth.signIn")}
          </Link>
        </>
      )}
      {status === "error" && (
        <>
          <h1 className="mb-2 text-xl font-semibold">{t("s.verification_failed")}</h1>
          <p className="text-sm text-red-600">{error}</p>
        </>
      )}
    </Card>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Suspense fallback={<Spinner />}>
        <VerifyEmailContent />
      </Suspense>
    </div>
  );
}
