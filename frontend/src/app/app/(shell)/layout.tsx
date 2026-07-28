"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LocalAuthGuard } from "@/components/layout/LocalAuthGuard";
import { SmbSidebar } from "@/components/layout/SmbSidebar";
import { SmbTopbar } from "@/components/layout/SmbTopbar";
import { Spinner } from "@/components/ui/Spinner";
import { CurrentBusinessProvider, useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";

function ShellContent({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { businesses, currentBusinessId, setCurrentBusinessId, isLoading } = useCurrentBusiness();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && businesses.length === 0) {
      router.replace("/app/onboarding");
    }
  }, [isLoading, businesses, router]);

  if (isLoading || (businesses.length === 0 && typeof window !== "undefined")) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex">
      <SmbSidebar isOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className="flex min-h-screen flex-1 flex-col">
        <SmbTopbar
          onMenuClick={() => setMobileNavOpen(true)}
          businesses={businesses}
          currentBusinessId={currentBusinessId}
          onBusinessChange={setCurrentBusinessId}
        />
        <main className="flex-1 p-4 sm:p-8">{children}</main>
      </div>
    </div>
  );
}

/**
 * Shared shell for every authenticated SMB Finance Manager page
 * (/app/dashboard, /app/sales, ...) — composes the local-auth guard,
 * the current-business context, and the responsive sidebar/topbar in one
 * place, unlike the AP-automation product's pages, which each hand-roll
 * this composition individually (see Sidebar.tsx/Topbar.tsx usage).
 */
export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <LocalAuthGuard>
      <CurrentBusinessProvider>
        <ShellContent>{children}</ShellContent>
      </CurrentBusinessProvider>
    </LocalAuthGuard>
  );
}
