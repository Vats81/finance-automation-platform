import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import { CustomerResponse, CustomerStatus } from "@/types/customer";

const STATUS_TONE: Record<CustomerStatus, "success" | "neutral"> = {
  active: "success",
  inactive: "neutral",
};

export function CustomerTable({ customers }: { customers: CustomerResponse[] }) {
  const { t } = useT();
  if (customers.length === 0) {
    return <p className="text-sm text-slate-500">{t("cust.none")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">{t("common.name")}</th>
          <th className="py-2 pr-4">{t("common.email")}</th>
          <th className="py-2 pr-4">{t("common.phone")}</th>
          <th className="py-2 pr-4">{t("cust.status")}</th>
        </tr>
      </thead>
      <tbody>
        {customers.map((customer) => (
          <tr key={customer.id} className="border-b border-slate-100 last:border-0">
            <td className="py-2 pr-4">
              <Link href={`/app/customers/${customer.id}`} className="font-medium text-brand-700 hover:underline">
                {customer.name}
              </Link>
            </td>
            <td className="py-2 pr-4 text-slate-600">{customer.email ?? "—"}</td>
            <td className="py-2 pr-4 text-slate-600">{customer.phone ?? "—"}</td>
            <td className="py-2 pr-4">
              <Badge tone={STATUS_TONE[customer.status]}>{t(`cust.status.${customer.status}` as MessageKey)}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
