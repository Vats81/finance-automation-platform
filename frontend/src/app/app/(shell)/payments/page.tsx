"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { listBusinessVendors } from "@/lib/api/businessVendors";
import { listCustomers } from "@/lib/api/customers";
import { listOutstandingPurchases } from "@/lib/api/purchases";
import { listOutstandingSales } from "@/lib/api/sales";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { PurchaseResponse } from "@/types/purchase";
import { SaleResponse } from "@/types/sale";

type DueBucket = "overdue" | "due_today" | "due_this_week" | "later" | "no_due_date";

interface PaymentRow {
  id: string;
  reference: string;
  counterparty: string;
  dueDate: string | null;
  outstandingAmount: string;
  paymentStatus: string;
  href: string;
}

const BUCKET_LABEL: Record<DueBucket, string> = {
  overdue: "Overdue",
  due_today: "Due today",
  due_this_week: "Due this week",
  later: "Later",
  no_due_date: "No due date",
};

const BUCKET_TONE: Record<DueBucket, "danger" | "warning" | "neutral"> = {
  overdue: "danger",
  due_today: "warning",
  due_this_week: "warning",
  later: "neutral",
  no_due_date: "neutral",
};

const PAYMENT_STATUS_TONE: Record<string, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

function getDueBucket(dueDate: string | null): DueBucket {
  if (!dueDate) return "no_due_date";

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);

  const diffDays = Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return "overdue";
  if (diffDays === 0) return "due_today";
  if (diffDays <= 7) return "due_this_week";
  return "later";
}

function salesToRows(sales: SaleResponse[], customerNames: Record<string, string>): PaymentRow[] {
  return sales.map((sale) => ({
    id: sale.id,
    reference: sale.invoice_number,
    counterparty: sale.customer_id ? (customerNames[sale.customer_id] ?? "—") : "Walk-in",
    dueDate: sale.due_date,
    outstandingAmount: sale.outstanding_amount,
    paymentStatus: sale.payment_status,
    href: `/app/sales/${sale.id}`,
  }));
}

function purchasesToRows(purchases: PurchaseResponse[], vendorNames: Record<string, string>): PaymentRow[] {
  return purchases.map((purchase) => ({
    id: purchase.id,
    reference: purchase.purchase_number,
    counterparty: vendorNames[purchase.vendor_id] ?? "—",
    dueDate: purchase.due_date,
    outstandingAmount: purchase.outstanding_amount,
    paymentStatus: purchase.payment_status,
    href: `/app/purchases/${purchase.id}`,
  }));
}

function PaymentsTable({ rows }: { rows: PaymentRow[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">Nothing outstanding.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Reference</th>
          <th className="py-2 pr-4">Counterparty</th>
          <th className="py-2 pr-4">Due date</th>
          <th className="py-2 pr-4">Due</th>
          <th className="py-2 pr-4">Outstanding</th>
          <th className="py-2 pr-4">Payment</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const bucket = getDueBucket(row.dueDate);
          return (
            <tr key={row.id} className="border-b border-slate-100 last:border-0">
              <td className="py-2 pr-4">
                <Link href={row.href} className="font-medium text-brand-700 hover:underline">
                  {row.reference}
                </Link>
              </td>
              <td className="py-2 pr-4 text-slate-600">{row.counterparty}</td>
              <td className="py-2 pr-4 text-slate-600">{row.dueDate ?? "—"}</td>
              <td className="py-2 pr-4">
                <Badge tone={BUCKET_TONE[bucket]}>{BUCKET_LABEL[bucket]}</Badge>
              </td>
              <td className="py-2 pr-4 text-slate-600">${row.outstandingAmount}</td>
              <td className="py-2 pr-4">
                <Badge tone={PAYMENT_STATUS_TONE[row.paymentStatus] ?? "neutral"}>
                  {row.paymentStatus.replace("_", " ")}
                </Badge>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function PaymentsPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [sales, setSales] = useState<SaleResponse[] | null>(null);
  const [purchases, setPurchases] = useState<PurchaseResponse[] | null>(null);
  const [customerNames, setCustomerNames] = useState<Record<string, string>>({});
  const [vendorNames, setVendorNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();

    Promise.all([
      listOutstandingSales(token, currentBusinessId),
      listOutstandingPurchases(token, currentBusinessId),
      listCustomers(token, currentBusinessId),
      listBusinessVendors(token, currentBusinessId),
    ])
      .then(([salesRes, purchasesRes, customersRes, vendorsRes]) => {
        setSales(salesRes);
        setPurchases(purchasesRes);
        setCustomerNames(Object.fromEntries(customersRes.items.map((c) => [c.id, c.name])));
        setVendorNames(Object.fromEntries(vendorsRes.items.map((v) => [v.id, v.legal_name])));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load payments"));
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Payments</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="space-y-6">
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Accounts Receivable</h2>
          {!sales && !error ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <PaymentsTable rows={salesToRows(sales ?? [], customerNames)} />
          )}
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold">Accounts Payable</h2>
          {!purchases && !error ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <PaymentsTable rows={purchasesToRows(purchases ?? [], vendorNames)} />
          )}
        </Card>
      </div>
    </div>
  );
}
