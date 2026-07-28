"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";

/**
 * Auth gate for the SMB Finance Manager product (/app/*), mirroring
 * AuthGuard.tsx for the AP-automation product but backed by useLocalAuth
 * instead of useAuth/MSAL — kept as a separate component rather than
 * parameterizing AuthGuard, since the two products' auth surfaces are
 * intentionally independent (see useLocalAuth.ts).
 */
export function LocalAuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useLocalAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/app/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return <>{children}</>;
}
