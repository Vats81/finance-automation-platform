"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AdminSidebar } from "@/components/layout/AdminSidebar";
import { Spinner } from "@/components/ui/Spinner";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";

/**
 * Guard for the platform Admin Panel — mirrors LocalAuthGuard's
 * redirect-in-useEffect pattern, plus an additional check that the logged-in
 * user actually has is_platform_admin set. Deliberately does not wrap
 * CurrentBusinessProvider (unlike the /app shell): the Admin Panel isn't
 * business-scoped.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useLocalAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/app/login");
      return;
    }
    if (!user?.is_platform_admin) {
      router.replace("/app/dashboard");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading || !isAuthenticated || !user?.is_platform_admin) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
