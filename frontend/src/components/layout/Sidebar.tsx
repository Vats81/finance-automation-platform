"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/vendors", label: "Vendors" },
  { href: "/purchase-orders", label: "Purchase Orders" },
  { href: "/invoices", label: "Invoices" },
  { href: "/approvals", label: "Approvals" },
  { href: "/payments", label: "Payments" },
  { href: "/audit", label: "Audit trail" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex h-screen w-56 flex-col border-r border-slate-200 bg-white p-4">
      <div className="mb-8 px-2 text-lg font-semibold text-brand-700">FAP</div>
      <ul className="space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`block rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
