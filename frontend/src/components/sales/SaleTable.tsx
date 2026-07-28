import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { SalePaymentStatus, SaleResponse } from "@/types/sale";

const STATUS_TONE: Record<SalePaymentStatus, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

export function SaleTable({ sales }: { sales: SaleResponse[] }) {
  if (sales.length === 0) {
    return <p className="text-sm text-slate-500">No sales recorded yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Invoice #</th>
          <th className="py-2 pr-4">Date</th>
          <th className="py-2 pr-4">Total</th>
          <th className="py-2 pr-4">Outstanding</th>
          <th className="py-2 pr-4">Payment status</th>
        </tr>
      </thead>
      <tbody>
        {sales.map((sale) => (
          <tr key={sale.id} className="border-b border-slate-100 last:border-0">
            <td className="py-2 pr-4">
              <Link href={`/app/sales/${sale.id}`} className="font-medium text-brand-700 hover:underline">
                {sale.invoice_number}
              </Link>
              {sale.status === "void" && (
                <span className="ml-2 text-xs text-slate-400">(void)</span>
              )}
            </td>
            <td className="py-2 pr-4 text-slate-600">{sale.invoice_date}</td>
            <td className="py-2 pr-4 text-slate-600">${sale.total_amount}</td>
            <td className="py-2 pr-4 text-slate-600">${sale.outstanding_amount}</td>
            <td className="py-2 pr-4">
              <Badge tone={STATUS_TONE[sale.payment_status]}>{sale.payment_status.replace("_", " ")}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
