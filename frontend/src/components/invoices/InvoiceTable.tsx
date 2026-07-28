"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { InvoiceResponse, InvoiceStatus } from "@/types/invoice";

const STATUS_TONE: Record<InvoiceStatus, "success" | "warning" | "danger" | "neutral"> = {
  submitted: "neutral",
  matched: "success",
  match_exception: "danger",
  pending_approval: "warning",
  approved: "success",
  rejected: "danger",
};

export function InvoiceTable({ invoices }: { invoices: InvoiceResponse[] }) {
  if (invoices.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">No invoices yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
        <tr>
          <th className="py-2 pr-4">Invoice #</th>
          <th className="py-2 pr-4">Total</th>
          <th className="py-2 pr-4">Status</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {invoices.map((invoice) => (
          <tr key={invoice.id} className="hover:bg-slate-50">
            <td className="py-3 pr-4">
              <Link href={`/invoices/${invoice.id}`} className="font-medium text-brand-700 hover:underline">
                {invoice.invoice_number}
              </Link>
            </td>
            <td className="py-3 pr-4">${invoice.total_amount}</td>
            <td className="py-3 pr-4">
              <Badge tone={STATUS_TONE[invoice.status]}>{invoice.status.replace("_", " ")}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
