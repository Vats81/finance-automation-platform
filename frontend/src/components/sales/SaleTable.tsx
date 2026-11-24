import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { MessageKey } from "@/lib/i18n/messages";
import { SalePaymentStatus, SaleResponse } from "@/types/sale";
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";

const STATUS_TONE: Record<SalePaymentStatus, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

export function SaleTable({ sales }: { sales: SaleResponse[] }) {
  const { t } = useT();
  if (sales.length === 0) {
    return <p className="text-sm text-slate-500">{t("sales.none")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">{t("sales.col.invoice")}</th>
          <th className="py-2 pr-4">{t("common.date")}</th>
          <th className="py-2 pr-4">{t("common.total")}</th>
          <th className="py-2 pr-4">{t("sales.col.outstanding")}</th>
          <th className="py-2 pr-4">{t("sales.col.status")}</th>
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
                <span className="ml-2 text-xs text-slate-400">({t("sales.void")})</span>
              )}
            </td>
            <td className="py-2 pr-4 text-slate-600">{sale.invoice_date}</td>
            <td className="py-2 pr-4 text-slate-600">{formatCurrency(sale.total_amount)}</td>
            <td className="py-2 pr-4 text-slate-600">{formatCurrency(sale.outstanding_amount)}</td>
            <td className="py-2 pr-4">
              <Badge tone={STATUS_TONE[sale.payment_status]}>{t(`sales.status.${sale.payment_status}` as MessageKey)}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
