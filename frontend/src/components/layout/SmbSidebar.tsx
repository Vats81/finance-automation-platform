"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { MessageKey } from "@/lib/i18n/messages";
import { useT } from "@/lib/i18n/LanguageProvider";

const NAV_ITEMS: { href: string; label: MessageKey }[] = [
  { href: "/app/dashboard", label: "nav.overview" },
  { href: "/app/sales", label: "nav.sales" },
  { href: "/app/udhaar", label: "nav.udhaar" },
  { href: "/app/summary", label: "nav.summary" },
  { href: "/app/expenses", label: "nav.expenses" },
  { href: "/app/purchases", label: "nav.purchases" },
  { href: "/app/inventory", label: "nav.inventory" },
  { href: "/app/customers", label: "nav.customers" },
  { href: "/app/vendors", label: "nav.vendors" },
  { href: "/app/payments", label: "nav.payments" },
  { href: "/app/data-upload", label: "nav.dataUpload" },
  { href: "/app/reports", label: "nav.reports" },
  { href: "/app/ai-assistant", label: "nav.aiAssistant" },
  { href: "/app/automations", label: "nav.automations" },
  { href: "/app/integrations", label: "nav.integrations" },
  { href: "/app/settings", label: "nav.settings" },
  { href: "/app/help", label: "nav.help" },
];

const PERSONAL_NAV_ITEMS: { href: string; label: MessageKey }[] = [
  { href: "/app/dashboard", label: "nav.overview" },
  { href: "/app/income", label: "nav.income" },
  { href: "/app/expenses", label: "nav.spending" },
  { href: "/app/budgets", label: "nav.budgets" },
  { href: "/app/data-upload", label: "nav.dataUpload" },
  { href: "/app/ai-assistant", label: "nav.aiAssistant" },
  { href: "/app/settings", label: "nav.settings" },
  { href: "/app/help", label: "nav.help" },
];

const FIRM_NAV_ITEMS: { href: string; label: MessageKey; exact: boolean }[] = [
  { href: "/app/firm", label: "nav.clients", exact: true },
  { href: "/app/firm/staff", label: "nav.staff", exact: true },
  { href: "/app/firm/billing", label: "nav.planBilling", exact: true },
];

function NavLink({
  href,
  label,
  isActive,
  onNavigate,
}: {
  href: string;
  label: MessageKey;
  isActive: boolean;
  onNavigate?: () => void;
}) {
  const { t } = useT();
  return (
    <li>
      <Link
        href={href}
        onClick={onNavigate}
        className={`block rounded-md px-3 py-2 text-sm font-medium ${
          isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
        }`}
      >
        {t(label)}
      </Link>
    </li>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { t } = useT();
  const { businesses, firms, currentFirm, currentBusiness } = useCurrentBusiness();
  const navItems = currentBusiness?.business.kind === "personal" ? PERSONAL_NAV_ITEMS : NAV_ITEMS;

  return (
    <div className="space-y-6">
      {firms.length > 0 && (
        <div>
          <div className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {currentFirm?.name ?? t("nav.firm")}
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
              {t("nav.business")}
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
  const { t } = useT();
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
                aria-label={t("nav.closeMenu")}
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
