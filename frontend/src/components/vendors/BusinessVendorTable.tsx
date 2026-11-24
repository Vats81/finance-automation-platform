import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { VendorResponse, VendorStatus } from "@/types/vendor";
import { useT } from "@/lib/i18n/LanguageProvider";

const STATUS_TONE: Record<VendorStatus, "neutral" | "success" | "warning"> = {
  pending_review: "warning",
  active: "success",
  inactive: "neutral",
};

export function BusinessVendorTable({ vendors }: { vendors: VendorResponse[] }) {
  const { t, label } = useT();
  if (vendors.length === 0) {
    return <p className="text-sm text-slate-500">{t("s.no_vendors_yet")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">{t("s.legal_name")}</th>
          <th className="py-2 pr-4">{t("s.contact_email_2")}</th>
          <th className="py-2 pr-4">{t("cust.status")}</th>
        </tr>
      </thead>
      <tbody>
        {vendors.map((vendor) => (
          <tr key={vendor.id} className="border-b border-slate-100 last:border-0">
            <td className="py-2 pr-4">
              <Link href={`/app/vendors/${vendor.id}`} className="font-medium text-brand-700 hover:underline">
                {vendor.legal_name}
              </Link>
            </td>
            <td className="py-2 pr-4 text-slate-600">{vendor.contact_email || "—"}</td>
            <td className="py-2 pr-4">
              {vendor.contact_email === "" ? (
                <Badge tone="neutral">{t("s.from_a_purchase")}</Badge>
              ) : (
                <Badge tone={STATUS_TONE[vendor.status]}>{label("vendor.status", vendor.status)}</Badge>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
