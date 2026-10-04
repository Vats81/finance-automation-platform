"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InstallAppButton } from "@/components/pwa/InstallAppButton";
import { submitContactRequest } from "@/lib/api/contact";
import { ApiError } from "@/lib/api/client";

const FEATURES = [
  { title: "Unified dashboard", body: "Revenue, expenses, profit, and cash flow in one view — updated the moment you record or import data." },
  { title: "Sales & expense tracking", body: "Record sales and purchases directly in the app, or import expenses, customers, vendors, and products from a CSV file." },
  { title: "Inventory intelligence", body: "Low-stock alerts, reorder suggestions, and fast vs. slow-moving product insights." },
  { title: "Payment tracking", body: "See every outstanding receivable and payable, and send reminders before they're overdue." },
  { title: "AI business assistant", body: "Ask questions about your own numbers in plain language and get answers with context." },
  { title: "Reports & alerts", body: "Download PDF reports anytime, or send them by email or WhatsApp with one click. Real-time alerts flag overdue payments and low stock automatically." },
];

const STEPS = [
  { step: "1", title: "Register your business", body: "Create an account and tell us a bit about your business — skip anything you're not sure of yet." },
  { step: "2", title: "Add your data", body: "Import customers, vendors, products, or expenses from a CSV file, and record your sales and purchases directly in the app." },
  { step: "3", title: "Get instant insight", body: "Your dashboard updates automatically, and AI-generated insights start surfacing what matters." },
  { step: "4", title: "Act on it", body: "Ask the AI assistant a question, download a report, or send one by email or WhatsApp." },
];

// Paid tiers ($29 / $79) used to be listed here, but billing isn't active
// (Settings itself said "plans are modeled, not billed, yet") — advertising
// prices nobody can pay is a trust problem. One early-access offer, listing
// only what exists today.
const EARLY_ACCESS_FEATURES = [
  "Dashboard with revenue, expenses, profit, and outstanding payments",
  "Track sales, purchases, expenses, inventory, customers, and vendors",
  "CSV import for customers, vendors, products, and expenses",
  "AI business assistant and insights",
  "Profit & Loss reports with PDF and CSV export",
  "Real-time alerts for overdue payments and low stock",
  "Invite teammates who already have an account",
];

const FAQS = [
  { q: "Do I need an accountant to use this?", a: "No. It's built for business owners without accounting or technical knowledge — it complements your accountant, not replaces full accounting software." },
  { q: "Can I manage more than one business?", a: "Yes. One account can hold multiple businesses or branches, each with its own data and team." },
  { q: "What file formats can I upload?", a: "CSV files for customers, vendors, products, and expenses. Sales and purchases are recorded directly in the app rather than imported." },
  { q: "How do reports get delivered?", a: "View them in-app, download as PDF, or send them by email or WhatsApp with one click. Scheduled, recurring delivery is coming soon." },
];

// This form used to flip to "Thanks — we'll be in touch shortly" on submit
// without sending the data anywhere. It now posts to the backend, which
// saves the request (and emails a notification if an inbox is configured),
// and only shows success once the server has actually accepted it.
function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState(""); // honeypot, never filled by a person
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await submitContactRequest({
        name,
        email,
        business_name: businessName || undefined,
        message: message || undefined,
        website: website || undefined,
      });
      setSubmitted(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Too many requests from your network just now — please try again in a while.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Please check your name and email and try again.");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong — please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <p className="text-sm text-emerald-700">
        Thanks — we&apos;ve received your request and will be in touch.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
      {error && (
        <p role="alert" className="text-sm text-red-600 sm:col-span-2">
          {error}
        </p>
      )}
      <input
        required
        maxLength={200}
        placeholder="Name"
        aria-label="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <input
        required
        type="email"
        placeholder="Work email"
        aria-label="Work email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <input
        maxLength={200}
        placeholder="Business name"
        aria-label="Business name"
        value={businessName}
        onChange={(e) => setBusinessName(e.target.value)}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm sm:col-span-2"
      />
      <textarea
        maxLength={2000}
        placeholder="What would you like to see in a demo?"
        aria-label="What would you like to see in a demo?"
        rows={3}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm sm:col-span-2"
      />
      {/* Honeypot: positioned off-screen and hidden from assistive tech, so
          people never see or fill it, while bots that fill every field do. */}
      <input
        type="text"
        name="website"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        value={website}
        onChange={(e) => setWebsite(e.target.value)}
        className="absolute left-[-9999px] h-0 w-0 opacity-0"
      />
      <Button type="submit" disabled={isSubmitting} className="sm:col-span-2">
        {isSubmitting ? "Sending…" : "Request a demo"}
      </Button>
    </form>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-white text-slate-900">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="text-lg font-semibold text-brand-700">FinanceAI</div>
        <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 sm:flex">
          <a href="#features" className="hover:text-slate-900">Features</a>
          <a href="#how-it-works" className="hover:text-slate-900">How it works</a>
          <a href="#pricing" className="hover:text-slate-900">Pricing</a>
          <a href="#faq" className="hover:text-slate-900">FAQ</a>
        </nav>
        <div className="flex items-center gap-3">
          <Link href="/app/login" className="text-sm font-medium text-slate-700 hover:text-slate-900">
            Log in
          </Link>
          <Link href="/app/signup">
            <Button>Sign up</Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-16 text-center sm:py-24">
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          Your AI Finance Manager for Business Growth
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600">
          Track your sales, expenses, and inventory — and get a clear picture of revenue, profit,
          cash flow, and what to do next, powered by AI. Built for small and medium businesses, not
          accountants.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/app/signup">
            <Button className="px-6 py-3 text-base">Get started free</Button>
          </Link>
          <a href="#contact">
            <Button variant="secondary" className="px-6 py-3 text-base">Request a demo</Button>
          </a>
          <InstallAppButton className="px-6 py-3 text-base" />
        </div>
        <p className="mt-3 text-xs text-slate-400">
          On iPhone/iPad: open this page in Safari, then Share → Add to Home Screen.
        </p>

        <div className="mx-auto mt-16 max-w-4xl rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm sm:p-8">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {["Revenue", "Expenses", "Profit margin", "Cash on hand"].map((label, i) => (
              <div key={label} className="rounded-lg bg-white p-4 text-left shadow-sm">
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
                <div className="mt-2 text-xl font-semibold text-brand-700">
                  {["$48.2k", "$21.7k", "34%", "$12.9k"][i]}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 h-32 rounded-lg bg-gradient-to-tr from-brand-50 to-brand-100" aria-hidden="true" />
        </div>
      </section>

      <section id="features" className="bg-slate-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-3xl font-bold">Everything your business needs, in one place</h2>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <Card key={f.title}>
                <h3 className="mb-2 font-semibold">{f.title}</h3>
                <p className="text-sm text-slate-600">{f.body}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-3xl font-bold">How it works</h2>
          <div className="mt-12 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s) => (
              <div key={s.step}>
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                  {s.step}
                </div>
                <h3 className="mb-1 font-semibold">{s.title}</h3>
                <p className="text-sm text-slate-600">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="bg-slate-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-3xl font-bold">Free during the private beta</h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-sm text-slate-600">
            We&apos;re in early access. Nobody is being charged, and paid plans aren&apos;t available yet.
          </p>
          <div className="mx-auto mt-12 max-w-md">
            <Card className="border-brand-500 ring-1 ring-brand-500">
              <h3 className="font-semibold">Early access</h3>
              <div className="mt-2 text-2xl font-bold">Free</div>
              <p className="mt-2 text-sm text-slate-600">
                Everything below, free while we&apos;re in private beta.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-slate-600">
                {EARLY_ACCESS_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <span className="text-brand-600">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link href="/app/signup" className="mt-6 block">
                <Button className="w-full">Join the private beta</Button>
              </Link>
            </Card>
          </div>
        </div>
      </section>

      <section id="faq" className="py-20">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-center text-3xl font-bold">Frequently asked questions</h2>
          <div className="mt-10 space-y-6">
            {FAQS.map((item) => (
              <div key={item.q}>
                <h3 className="font-semibold">{item.q}</h3>
                <p className="mt-1 text-sm text-slate-600">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="contact" className="bg-slate-50 py-20">
        <div className="mx-auto max-w-2xl px-6">
          <h2 className="text-center text-3xl font-bold">See it in action</h2>
          <p className="mx-auto mt-3 max-w-md text-center text-sm text-slate-600">
            Tell us about your business and we&apos;ll set up a personalized walkthrough.
          </p>
          <Card className="mt-8">
            <ContactForm />
          </Card>
        </div>
      </section>

      <footer className="border-t border-slate-200 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-slate-500 sm:flex-row">
          <span>© {new Date().getFullYear()} FinanceAI</span>
          <div className="flex gap-6">
            <Link href="/terms" className="hover:text-slate-800">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-slate-800">Privacy Policy</Link>
            <Link href="/app/login" className="hover:text-slate-800">Log in</Link>
            <Link href="/app/signup" className="hover:text-slate-800">Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
