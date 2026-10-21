"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { joinWaitlist } from "@/lib/api/betaWaitlist";

const BOOKKEEPING_OPTIONS = [
  "Spreadsheets",
  "Paper / notebook",
  "Accounting software",
  "An accountant or bookkeeper",
  "Mostly in my head",
  "Other",
];

/**
 * Private-beta interest form. Intentionally not linked from the site: it is
 * shared only with people we choose to tell about the beta. Joining registers
 * interest and nothing else — no account is created and no access is granted.
 */
export default function BetaWaitlistPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [businessType, setBusinessType] = useState("");
  const [method, setMethod] = useState("");
  const [problem, setProblem] = useState("");
  const [weeklyFeedback, setWeeklyFeedback] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [website, setWebsite] = useState(""); // honeypot
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await joinWaitlist({
        name,
        work_email: email,
        business_name: businessName || undefined,
        business_type: businessType || undefined,
        bookkeeping_method: method || undefined,
        reporting_problem: problem || undefined,
        weekly_feedback_ok: weeklyFeedback,
        acknowledged,
        website: website || undefined,
      });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Too many requests from your network just now — please try again in a while.");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong — please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-4 py-12">
      <h1 className="mb-2 text-2xl font-semibold">FinanceAI private beta</h1>
      <p className="mb-6 text-sm text-slate-600">
        FinanceAI is a bookkeeping and reporting assistant for small businesses. We are opening a small, free,
        supervised beta for a handful of businesses that keep their books in spreadsheets today. Registering
        interest does <strong>not</strong> create an account or give access: we review each request, set up
        every beta business together, and will email you if there is a place.
      </p>

      {done ? (
        <div className="rounded-md bg-emerald-50 p-4 text-sm text-emerald-800">
          Thanks — your interest is registered. We&apos;ll be in touch only if we can offer you a place.{" "}
          <Link href="/" className="underline">
            Back to the home page
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
          <FormField label="Your name">
            <Input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
          </FormField>
          <FormField label="Work email">
            <Input
              required
              type="email"
              maxLength={320}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
          <FormField label="Business name (optional)">
            <Input maxLength={200} value={businessName} onChange={(e) => setBusinessName(e.target.value)} />
          </FormField>
          <FormField label="What kind of business is it?">
            <Input
              maxLength={100}
              placeholder="e.g. online shop, freelancer, agency, home bakery"
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
            />
          </FormField>
          <FormField label="How do you keep your books today?">
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Choose one</option>
              {BOOKKEEPING_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="What is the main reporting problem you want solved?">
            <textarea
              maxLength={1000}
              rows={4}
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </FormField>

          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={weeklyFeedback}
              onChange={(e) => setWeeklyFeedback(e.target.checked)}
              className="mt-1"
            />
            I&apos;m willing to give short feedback every week during the beta.
          </label>
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              required
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-1"
            />
            I understand this is a private, supervised beta, and that I should not send bank details,
            passwords or real financial files through this form.
          </label>

          {/* Honeypot: off-screen and hidden from assistive tech. */}
          <div aria-hidden="true" style={{ position: "absolute", left: "-10000px" }}>
            <input
              tabIndex={-1}
              autoComplete="off"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              aria-label="Leave this field empty"
            />
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Sending..." : "Register my interest"}
          </Button>
        </form>
      )}
    </main>
  );
}
