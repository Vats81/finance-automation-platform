"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { registerUser } from "@/lib/api/auth";

export default function SignupPage() {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registered, setRegistered] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await registerUser({ email, password, display_name: displayName });
      setRegistered(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create your account");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (registered) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <Card className="w-full max-w-sm text-center">
          <h1 className="mb-2 text-xl font-semibold">Check your email</h1>
          <p className="text-sm text-slate-600">
            We sent a verification link to <span className="font-medium">{email}</span>. Verify your
            email to activate your account, then{" "}
            <Link href="/app/login" className="text-brand-600 underline">
              sign in
            </Link>
            .
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold">Create your account</h1>
        <p className="mb-6 text-sm text-slate-500">Your AI Finance Manager for Business Growth</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          <FormField label="Full name">
            <Input required value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </FormField>
          <FormField label="Email">
            <Input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
          <FormField label="Password">
            <Input
              required
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </FormField>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-400">
          By creating an account, you agree to our{" "}
          <Link href="/terms" className="underline hover:text-slate-600">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="underline hover:text-slate-600">
            Privacy Policy
          </Link>
          .
        </p>

        <p className="mt-4 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/app/login" className="text-brand-600 underline">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
