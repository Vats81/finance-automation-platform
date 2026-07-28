"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/businesses", label: "Businesses" },
  { href: "/admin/users", label: "Users" },
];

/**
 * Left nav for the platform Admin Panel — deliberately its own small
 * sidebar rather than reusing SmbSidebar, since this area isn't
 * business-scoped and has a very different, much shorter nav list.
 */
export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex h-screen w-56 flex-col border-r border-slate-200 bg-white p-4">
      <div className="mb-8 px-2 text-lg font-semibold text-brand-700">FinanceAI Admin</div>
      <ul className="flex-1 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
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
      <Link href="/app/dashboard" className="px-3 py-2 text-sm text-slate-500 hover:underline">
        ← Back to app
      </Link>
    </nav>
  );
}
