"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { getIntegrationsStatus } from "@/lib/api/integrations";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { IntegrationsStatusResponse, ProviderStatus } from "@/types/integrations";

const COMING_LATER = ["QuickBooks", "Zoho Books", "Tally", "Live Google Sheets sync"];

function StatusCard({ name, status }: { name: string; status: ProviderStatus }) {
  return (
    <div className="rounded-md border border-slate-200 p-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-slate-900">{name}</span>
        <Badge tone={status.connected ? "success" : "neutral"}>
          {status.connected ? "Connected" : "Not configured"}
        </Badge>
      </div>
      <p className="text-xs text-slate-500">{status.detail}</p>
    </div>
  );
}

export default function IntegrationsPage() {
  const { getAccessToken } = useLocalAuth();
  const [status, setStatus] = useState<IntegrationsStatusResponse | null>(null);

  useEffect(() => {
    getIntegrationsStatus(getAccessToken())
      .then(setStatus)
      .catch(() => undefined);
  }, [getAccessToken]);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Integrations</h1>
      <p className="mb-6 text-sm text-slate-500">
        See which services this app is actually connected to, and where to move data in the meantime.
      </p>

      <Card className="mb-6">
        <h2 className="mb-4 text-sm font-semibold">Connected services</h2>
        {status ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <StatusCard name="Email" status={status.email} />
            <StatusCard name="WhatsApp" status={status.whatsapp} />
            <StatusCard name="AI Assistant" status={status.ai_assistant} />
            <StatusCard name="Document storage" status={status.document_storage} />
            <StatusCard name="Billing" status={status.billing} />
          </div>
        ) : (
          <p className="text-sm text-slate-500">Loading...</p>
        )}
      </Card>

      <Card className="mb-6">
        <h2 className="mb-4 text-sm font-semibold">Move your data</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Link
            href="/app/data-upload"
            className="rounded-md border border-slate-200 p-4 hover:border-brand-400 hover:bg-slate-50"
          >
            <div className="text-sm font-medium text-slate-900">Import from CSV</div>
            <p className="mt-1 text-xs text-slate-500">
              Bring in customers, vendors, products, or expenses from a spreadsheet via the Data Upload
              Centre.
            </p>
          </Link>
          <Link
            href="/app/reports"
            className="rounded-md border border-slate-200 p-4 hover:border-brand-400 hover:bg-slate-50"
          >
            <div className="text-sm font-medium text-slate-900">Export as CSV or PDF</div>
            <p className="mt-1 text-xs text-slate-500">
              Download your Profit &amp; Loss report to open in Excel, Google Sheets, or share with your
              accountant.
            </p>
          </Link>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">Coming later</h2>
        <ul className="flex flex-wrap gap-2">
          {COMING_LATER.map((name) => (
            <li key={name}>
              <Badge tone="neutral">{name}</Badge>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
