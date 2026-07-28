"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { fetchMe } from "@/lib/api/identity";
import { useAuth } from "@/lib/auth/useAuth";
import { UserResponse } from "@/types/user";

function DashboardContent() {
  const { getAccessToken } = useAuth();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken()
      .then((token) => fetchMe(token))
      .then(setUser)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load profile"));
  }, [getAccessToken]);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={user} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">Dashboard</h1>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <div className="text-sm text-slate-500">Signed in as</div>
              <div className="mt-1 text-lg font-semibold">{user?.display_name ?? "…"}</div>
              <div className="text-xs text-slate-400">{user?.email}</div>
            </Card>
            <Card>
              <div className="text-sm text-slate-500">Role</div>
              <div className="mt-1 text-lg font-semibold capitalize">
                {user?.role.replace("_", " ") ?? "…"}
              </div>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}
