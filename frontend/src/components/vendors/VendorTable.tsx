"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { VendorResponse, VendorStatus } from "@/types/vendor";

const STATUS_TONE: Record<VendorStatus, "success" | "warning" | "neutral"> = {
  active: "success",
  pending_review: "warning",
  inactive: "neutral",
};

export function VendorTable({ vendors }: { vendors: VendorResponse[] }) {
  if (vendors.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">No vendors yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
        <tr>
          <th className="py-2 pr-4">Legal name</th>
          <th className="py-2 pr-4">Contact</th>
          <th className="py-2 pr-4">Tax ID</th>
          <th className="py-2 pr-4">W-9</th>
          <th className="py-2 pr-4">Status</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {vendors.map((vendor) => (
          <tr key={vendor.id} className="hover:bg-slate-50">
            <td className="py-3 pr-4">
              <Link href={`/vendors/${vendor.id}`} className="font-medium text-brand-700 hover:underline">
                {vendor.legal_name}
              </Link>
            </td>
            <td className="py-3 pr-4 text-slate-600">{vendor.contact_email}</td>
            <td className="py-3 pr-4 font-mono text-slate-500">{vendor.tax_id_masked}</td>
            <td className="py-3 pr-4">{vendor.has_w9_on_file ? "On file" : "Missing"}</td>
            <td className="py-3 pr-4">
              <Badge tone={STATUS_TONE[vendor.status]}>{vendor.status.replace("_", " ")}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
