"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/app/dashboard", label: "Overview" },
  { href: "/app/sales", label: "Sales" },
  { href: "/app/expenses", label: "Expenses" },
  { href: "/app/purchases", label: "Purchases" },
  { href: "/app/inventory", label: "Inventory" },
  { href: "/app/customers", label: "Customers" },
  { href: "/app/vendors", label: "Vendors" },
  { href: "/app/payments", label: "Payments" },
  { href: "/app/data-upload", label: "Data Upload" },
  { href: "/app/reports", label: "Reports" },
  { href: "/app/ai-assistant", label: "AI Assistant" },
  { href: "/app/automations", label: "Automations" },
  { href: "/app/integrations", label: "Integrations" },
  { href: "/app/settings", label: "Settings" },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <ul className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const isActive = pathname?.startsWith(item.href);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
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
  );
}

/**
 * Responsive left nav for the SMB Finance Manager product: a fixed sidebar
 * on desktop/tablet, an off-canvas drawer on mobile — unlike the existing
 * AP-automation Sidebar.tsx, which has no responsive handling at all.
 */
export function SmbSidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  return (
    <>
      <nav className="hidden h-screen w-56 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-8 px-2 text-lg font-semibold text-brand-700">FinanceAI</div>
        <NavList />
      </nav>

      {isOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={onClose} aria-hidden="true" />
          <nav className="absolute left-0 top-0 flex h-full w-64 flex-col bg-white p-4 shadow-xl">
            <div className="mb-8 flex items-center justify-between px-2">
              <span className="text-lg font-semibold text-brand-700">FinanceAI</span>
              <button
                onClick={onClose}
                aria-label="Close menu"
                className="rounded-md p-1 text-slate-500 hover:bg-slate-100"
              >
                ✕
              </button>
            </div>
            <NavList onNavigate={onClose} />
          </nav>
        </div>
      )}
    </>
  );
}
