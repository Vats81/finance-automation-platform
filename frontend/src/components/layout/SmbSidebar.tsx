"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";

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
  { href: "/app/help", label: "Help" },
];

const PERSONAL_NAV_ITEMS = [
  { href: "/app/dashboard", label: "Overview" },
  { href: "/app/income", label: "Income" },
  { href: "/app/expenses", label: "Spending" },
  { href: "/app/budgets", label: "Budgets" },
  { href: "/app/data-upload", label: "Data Upload" },
  { href: "/app/ai-assistant", label: "AI Assistant" },
  { href: "/app/settings", label: "Settings" },
  { href: "/app/help", label: "Help" },
];

const FIRM_NAV_ITEMS = [
  { href: "/app/firm", label: "Clients", exact: true },
  { href: "/app/firm/staff", label: "Staff", exact: true },
];

function NavLink({
  href,
  label,
  isActive,
  onNavigate,
}: {
  href: string;
  label: string;
  isActive: boolean;
  onNavigate?: () => void;
}) {
  return (
    <li>
      <Link
        href={href}
        onClick={onNavigate}
        className={`block rounded-md px-3 py-2 text-sm font-medium ${
          isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
        }`}
      >
        {label}
      </Link>
    </li>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { businesses, firms, currentFirm, currentBusiness } = useCurrentBusiness();
  const navItems = currentBusiness?.business.kind === "personal" ? PERSONAL_NAV_ITEMS : NAV_ITEMS;

  return (
    <div className="space-y-6">
      {firms.length > 0 && (
        <div>
          <div className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {currentFirm?.name ?? "Firm"}
          </div>
          <ul className="space-y-1">
            {FIRM_NAV_ITEMS.map((item) => (
              <NavLink
                key={item.href}
                href={item.href}
                label={item.label}
                isActive={pathname === item.href}
                onNavigate={onNavigate}
              />
            ))}
          </ul>
        </div>
      )}
      {businesses.length > 0 && (
        <div>
          {firms.length > 0 && (
            <div className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Business
            </div>
          )}
          <ul className="space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.href}
                href={item.href}
                label={item.label}
                isActive={pathname?.startsWith(item.href) ?? false}
                onNavigate={onNavigate}
              />
            ))}
          </ul>
        </div>
      )}
    </div>
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
        <div className="mb-8 px-2 text-xl font-bold tracking-tight text-brand-700">Finverlo</div>
        <NavList />
      </nav>

      {isOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={onClose} aria-hidden="true" />
          <nav className="absolute left-0 top-0 flex h-full w-64 flex-col bg-white p-4 shadow-xl">
            <div className="mb-8 flex items-center justify-between px-2">
              <span className="text-xl font-bold tracking-tight text-brand-700">Finverlo</span>
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
