import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { PurchasePaymentStatus, PurchaseResponse } from "@/types/purchase";

const STATUS_TONE: Record<PurchasePaymentStatus, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

export function PurchaseTable({ purchases }: { purchases: PurchaseResponse[] }) {
  if (purchases.length === 0) {
    return <p className="text-sm text-slate-500">No purchases recorded yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Purchase #</th>
          <th className="py-2 pr-4">Date</th>
          <th className="py-2 pr-4">Total</th>
          <th className="py-2 pr-4">Outstanding</th>
          <th className="py-2 pr-4">Payment status</th>
        </tr>
      </thead>
      <tbody>
        {purchases.map((purchase) => (
          <tr key={purchase.id} className="border-b border-slate-100 last:border-0">
            <td className="py-2 pr-4">
              <Link
                href={`/app/purchases/${purchase.id}`}
                className="font-medium text-brand-700 hover:underline"
              >
                {purchase.purchase_number}
              </Link>
              {purchase.status === "void" && <span className="ml-2 text-xs text-slate-400">(void)</span>}
            </td>
            <td className="py-2 pr-4 text-slate-600">{purchase.purchase_date}</td>
            <td className="py-2 pr-4 text-slate-600">${purchase.total_amount}</td>
            <td className="py-2 pr-4 text-slate-600">${purchase.outstanding_amount}</td>
            <td className="py-2 pr-4">
              <Badge tone={STATUS_TONE[purchase.payment_status]}>
                {purchase.payment_status.replace("_", " ")}
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
