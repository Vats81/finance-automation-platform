"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { isAuthDevMode } from "@/lib/auth/msalConfig";
import { useAuth } from "@/lib/auth/useAuth";

export default function LoginPage() {
  const { loginDev, loginMsal, isAuthenticated } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("ap.clerk@example.com");
  const [name, setName] = useState("Alex Clerk");

  if (isAuthenticated) {
    router.replace("/dashboard");
    return null;
  }

  function handleDevLogin(event: FormEvent) {
    event.preventDefault();
    loginDev({ oid: `dev-${email}`, email, name });
    router.push("/dashboard");
  }

  return (
    <div className="flex h-screen items-center justify-center bg-slate-50">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold">Finance Automation Platform</h1>
        <p className="mb-6 text-sm text-slate-500">Invoice / AP Automation</p>

        {isAuthDevMode ? (
          <form onSubmit={handleDevLogin} className="space-y-4">
            <div className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Dev-mode sign-in — no real Entra ID tenant required. Role is assigned via the
              Finance Admin&apos;s /users endpoint after first login.
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Email</label>
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Display name</label>
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">
              Sign in
            </Button>
          </form>
        ) : (
          <Button className="w-full" onClick={() => loginMsal()}>
            Sign in with Microsoft
          </Button>
        )}
      </Card>
    </div>
  );
}
