"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InstallAppButton } from "@/components/pwa/InstallAppButton";

const FEATURES = [
  { title: "Unified dashboard", body: "Revenue, expenses, profit, and cash flow in one view — updated the moment you upload data." },
  { title: "Sales & expense tracking", body: "Log transactions manually or import from CSV/Excel, with categorization and duplicate detection." },
  { title: "Inventory intelligence", body: "Low-stock alerts, reorder suggestions, and fast vs. slow-moving product insights." },
  { title: "Payment tracking", body: "See every outstanding receivable and payable, and send reminders before they're overdue." },
  { title: "AI business assistant", body: "Ask questions about your own numbers in plain language and get answers with context." },
  { title: "Automated reports", body: "Daily, weekly, and monthly reports — downloadable as PDF, delivered by email or WhatsApp." },
];

const STEPS = [
  { step: "1", title: "Register your business", body: "Create an account and tell us a bit about your business — skip anything you're not sure of yet." },
  { step: "2", title: "Upload your data", body: "Import sales, expenses, purchases, inventory, or customer records from CSV or Excel." },
  { step: "3", title: "Get instant insight", body: "Your dashboard updates automatically, and AI-generated insights start surfacing what matters." },
  { step: "4", title: "Act on it", body: "Ask the AI assistant a question, download a report, or set up an automated alert." },
];

const PLANS = [
  {
    name: "Starter",
    price: "Free",
    description: "For a single business just getting started.",
    features: ["One business", "Basic dashboard", "CSV & Excel uploads", "Monthly reports", "Limited AI insights"],
  },
  {
    name: "Growth",
    price: "$29/mo",
    description: "For a growing business that needs more automation.",
    features: ["Multiple users", "Daily & weekly reports", "Inventory intelligence", "AI assistant", "WhatsApp reports", "Payment reminders"],
    highlighted: true,
  },
  {
    name: "Professional",
    price: "$79/mo",
    description: "For multi-branch businesses that need forecasting.",
    features: ["Multiple branches", "Advanced forecasting", "Advanced automations", "More integrations", "Priority support"],
  },
];

const FAQS = [
  { q: "Do I need an accountant to use this?", a: "No. It's built for business owners without accounting or technical knowledge — it complements your accountant, not replaces full accounting software." },
  { q: "Can I manage more than one business?", a: "Yes. One account can hold multiple businesses or branches, each with its own data and team." },
  { q: "What file formats can I upload?", a: "CSV and Excel (.xlsx/.xls) for sales, expenses, purchases, inventory, customers, and vendors." },
  { q: "How do reports get delivered?", a: "View them in-app, download as PDF, or have them sent automatically by email or WhatsApp." },
];

function ContactForm() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
  }

  if (submitted) {
    return <p className="text-sm text-emerald-700">Thanks — we&apos;ll be in touch shortly.</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
      <input required placeholder="Name" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
      <input required type="email" placeholder="Work email" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
      <input placeholder="Business name" className="rounded-md border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
      <textarea placeholder="What would you like to see in a demo?" rows={3} className="rounded-md border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
      <Button type="submit" className="sm:col-span-2">Request a demo</Button>
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
          Upload your sales, expenses, and inventory data — and get a clear picture of revenue, profit,
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
          <h2 className="text-center text-3xl font-bold">Simple, transparent pricing</h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-sm text-slate-600">
            Start free. Upgrade as your business grows. Cancel anytime.
          </p>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
            {PLANS.map((plan) => (
              <Card
                key={plan.name}
                className={plan.highlighted ? "border-brand-500 ring-1 ring-brand-500" : undefined}
              >
                <h3 className="font-semibold">{plan.name}</h3>
                <div className="mt-2 text-2xl font-bold">{plan.price}</div>
                <p className="mt-2 text-sm text-slate-600">{plan.description}</p>
                <ul className="mt-4 space-y-2 text-sm text-slate-600">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <span className="text-brand-600">✓</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link href="/app/signup" className="mt-6 block">
                  <Button
                    variant={plan.highlighted ? "primary" : "secondary"}
                    className="w-full"
                  >
                    Start free trial
                  </Button>
                </Link>
              </Card>
            ))}
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
