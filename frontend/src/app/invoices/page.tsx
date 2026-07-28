"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { InvoiceTable } from "@/components/invoices/InvoiceTable";
import { listInvoices } from "@/lib/api/invoices";
import { useAuth } from "@/lib/auth/useAuth";
import { InvoiceResponse } from "@/types/invoice";

function InvoicesContent() {
  const { getAccessToken } = useAuth();
  const [invoices, setInvoices] = useState<InvoiceResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken()
      .then((token) => listInvoices(token))
      .then((page) => setInvoices(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load invoices"));
  }, [getAccessToken]);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-semibold">Invoices</h1>
            <Link href="/invoices/new">
              <Button>Submit invoice</Button>
            </Link>
          </div>
          <Card>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {!invoices && !error ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : (
              <InvoiceTable invoices={invoices ?? []} />
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function InvoicesPage() {
  return (
    <AuthGuard>
      <InvoicesContent />
    </AuthGuard>
  );
}
