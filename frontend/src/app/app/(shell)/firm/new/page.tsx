"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { createFirm } from "@/lib/api/firms";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useSubmissionKey } from "@/lib/idempotency";

export default function NewFirmPage() {
  const { getAccessToken } = useLocalAuth();
  const { firms, refresh } = useCurrentBusiness();
  const router = useRouter();
  const submission = useSubmissionKey();
  const [name, setName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await createFirm(getAccessToken(), name.trim(), { idempotencyKey: submission.key() });
      await refresh(); // the Firm section appears in the menu
      router.push("/app/firm");
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setError(err instanceof Error ? err.message : "Failed to create your firm");
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Set up an accounting firm</h1>
      <Card className="max-w-lg">
        <p className="mb-4 text-sm text-slate-500">
          You&apos;ll be the firm&apos;s owner. Next you can add your clients&apos; businesses and your own staff.
          Your existing business is not changed.
        </p>
        {firms.length > 0 && (
          <p className="mb-4 text-sm text-amber-700">You already work for {firms.map((f) => f.name).join(", ")}.</p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          <FormField label="Firm name">
            <Input required maxLength={255} value={name} onChange={(e) => setName(e.target.value)} />
          </FormField>
          <Button type="submit" disabled={isSubmitting || !name.trim()}>
            {isSubmitting ? "Creating…" : "Create firm"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
