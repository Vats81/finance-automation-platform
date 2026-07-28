"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { requestPasswordReset } from "@/lib/api/auth";

export default function ForgotPasswordPage() {
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
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold">Reset your password</h1>
        <p className="mb-6 text-sm text-slate-500">
          Enter your email and we&apos;ll send you a reset link.
        </p>

        {submitted ? (
          <p className="text-sm text-slate-600">
            If an account exists for <span className="font-medium">{email}</span>, a reset link is on
            its way.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <FormField label="Email">
              <Input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </FormField>
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link href="/app/login" className="text-brand-600 underline">
            Back to sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
