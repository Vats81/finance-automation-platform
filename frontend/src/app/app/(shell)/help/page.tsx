"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useTour } from "@/lib/tour/useTour";

interface HelpTopic {
  title: string;
  points: string[];
}

const TOPICS: HelpTopic[] = [
  {
    title: "Getting started",
    points: [
      "After signing up, complete your business profile from the onboarding screen — every field is optional and can be filled in later from Settings.",
      "Use the business switcher in the top bar if your account belongs to more than one business.",
    ],
  },
  {
    title: "Sales",
    points: [
      "Sales → New sale to record a sale, with one or more line items and an optional customer.",
      "Open any sale and click Edit to change its details, line items, or totals — you can't edit a voided sale.",
      "Record a partial or full payment from the sale's detail page; the payment status updates automatically.",
      "Void a sale instead of deleting it — voided sales stay visible for your records but can no longer be edited or paid.",
    ],
  },
  {
    title: "Purchases",
    points: [
      "Purchases → New purchase to record a purchase from a vendor, optionally linking each line item to a product.",
      "Same as Sales: open a purchase and click Edit to change it, or Void to close it out. Editing is blocked once a purchase is void.",
    ],
  },
  {
    title: "Expenses",
    points: [
      "Expenses → New expense to log a business expense, with an optional vendor link and receipt scan (if AI is configured).",
    ],
  },
  {
    title: "Inventory",
    points: [
      "Inventory → New product to add a product, then use Adjust stock on its detail page to record stock in/out with a reason.",
      "Products below their minimum stock level are flagged automatically on the dashboard and notifications.",
    ],
  },
  {
    title: "Customers & Vendors",
    points: ["Manage your customer and vendor directory — both support search, editing, and deactivation."],
  },
  {
    title: "Payments",
    points: [
      "The Payments page shows every outstanding receivable and payable in one place, bucketed by how overdue they are.",
    ],
  },
  {
    title: "Reports & data",
    points: [
      "Reports gives you a Profit & Loss breakdown by day, week, or month, exportable as CSV or PDF, or sent by email/WhatsApp.",
      "Data Upload lets you bulk-import customers, vendors, products, or expenses from a CSV file.",
    ],
  },
  {
    title: "AI Assistant",
    points: [
      "Ask questions about your business in plain language from the AI Assistant page — it answers using your real data.",
    ],
  },
  {
    title: "Team & billing",
    points: [
      "Settings → Team members to invite teammates (they need an existing account) and manage their roles.",
      "Settings → Plan to see your current plan and upgrade — this may redirect to a real checkout if billing is enabled.",
    ],
  },
];

export default function HelpPage() {
  const { restart } = useTour();

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Help</h1>
        <Button variant="secondary" onClick={restart}>
          Take the tour
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {TOPICS.map((topic) => (
          <Card key={topic.title}>
            <h2 className="mb-2 text-sm font-semibold text-slate-900">{topic.title}</h2>
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
              {topic.points.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>

      <p className="mt-6 text-sm text-slate-500">
        Something not covered here? Check{" "}
        <Link href="/app/integrations" className="text-brand-600 underline">
          Integrations
        </Link>{" "}
        to see which optional features (email, WhatsApp, AI, billing) are connected.
      </p>
    </div>
  );
}
