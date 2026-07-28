"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getPlatformStats } from "@/lib/api/admin";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { PlatformStats } from "@/types/admin";

export default function AdminOverviewPage() {
  const { getAccessToken } = useLocalAuth();
  const [stats, setStats] = useState<PlatformStats | null>(null);

  useEffect(() => {
    getPlatformStats(getAccessToken())
      .then(setStats)
      .catch(() => undefined);
  }, [getAccessToken]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Platform Overview</h1>

      {!stats ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <div className="text-sm font-medium text-slate-500">Total businesses</div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">{stats.total_businesses}</div>
            </Card>
            <Card>
              <div className="text-sm font-medium text-slate-500">Total users</div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">{stats.total_users}</div>
            </Card>
            <Card>
              <div className="text-sm font-medium text-slate-500">Verified users</div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">{stats.verified_users}</div>
            </Card>
            <Card>
              <div className="text-sm font-medium text-slate-500">Unverified users</div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">{stats.unverified_users}</div>
            </Card>
          </div>

          <Card className="mt-6">
            <h2 className="mb-4 text-sm font-semibold">Businesses by plan</h2>
            {Object.keys(stats.businesses_by_plan).length === 0 ? (
              <p className="text-sm text-slate-500">No businesses yet.</p>
            ) : (
              <div className="flex flex-wrap gap-6">
                {Object.entries(stats.businesses_by_plan).map(([plan, count]) => (
                  <div key={plan}>
                    <div className="text-xs uppercase text-slate-500">{plan}</div>
                    <div className="text-xl font-semibold text-slate-900">{count}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
