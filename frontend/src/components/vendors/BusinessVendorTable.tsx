import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { VendorResponse, VendorStatus } from "@/types/vendor";

const STATUS_TONE: Record<VendorStatus, "neutral" | "success" | "warning"> = {
  pending_review: "warning",
  active: "success",
  inactive: "neutral",
};

export function BusinessVendorTable({ vendors }: { vendors: VendorResponse[] }) {
  if (vendors.length === 0) {
    return <p className="text-sm text-slate-500">No vendors yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Legal name</th>
          <th className="py-2 pr-4">Contact email</th>
          <th className="py-2 pr-4">Status</th>
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
            <td className="py-2 pr-4 text-slate-600">{vendor.contact_email}</td>
            <td className="py-2 pr-4">
              <Badge tone={STATUS_TONE[vendor.status]}>{vendor.status.replace("_", " ")}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
