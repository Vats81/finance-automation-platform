import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { CustomerResponse, CustomerStatus } from "@/types/customer";

const STATUS_TONE: Record<CustomerStatus, "success" | "neutral"> = {
  active: "success",
  inactive: "neutral",
};

export function CustomerTable({ customers }: { customers: CustomerResponse[] }) {
  if (customers.length === 0) {
    return <p className="text-sm text-slate-500">No customers yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Name</th>
          <th className="py-2 pr-4">Email</th>
          <th className="py-2 pr-4">Phone</th>
          <th className="py-2 pr-4">Status</th>
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
              <Badge tone={STATUS_TONE[customer.status]}>{customer.status}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
