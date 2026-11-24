import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { PurchasePaymentStatus, PurchaseResponse } from "@/types/purchase";
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";

const STATUS_TONE: Record<PurchasePaymentStatus, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

export function PurchaseTable({
  purchases,
  vendorNames = {},
}: {
  purchases: PurchaseResponse[];
  vendorNames?: Record<string, string>;
}) {
  const { t, label } = useT();
  if (purchases.length === 0) {
    return <p className="text-sm text-slate-500">{t("s.no_purchases_recorded_yet")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">{t("s.purchase")}</th>
          <th className="py-2 pr-4">{t("s.vendor")}</th>
          <th className="py-2 pr-4">{t("common.date")}</th>
          <th className="py-2 pr-4">{t("common.total")}</th>
          <th className="py-2 pr-4">{t("sales.col.outstanding")}</th>
          <th className="py-2 pr-4">{t("sales.col.status")}</th>
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
              {purchase.status === "void" && <span className="ml-2 text-xs text-slate-400">{t("s.void")}</span>}
            </td>
            <td className="py-2 pr-4 text-slate-600">
              {purchase.vendor_name ?? (purchase.vendor_id ? vendorNames[purchase.vendor_id] : undefined) ?? "—"}
            </td>
            <td className="py-2 pr-4 text-slate-600">{purchase.purchase_date}</td>
            <td className="py-2 pr-4 text-slate-600">{formatCurrency(purchase.total_amount)}</td>
            <td className="py-2 pr-4 text-slate-600">{formatCurrency(purchase.outstanding_amount)}</td>
            <td className="py-2 pr-4">
              <Badge tone={STATUS_TONE[purchase.payment_status]}>
                {label("sales.status", purchase.payment_status)}
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
