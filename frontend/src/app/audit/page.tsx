"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import { listAuditLog } from "@/lib/api/audit";
import { useAuth } from "@/lib/auth/useAuth";
import { AuditLogEntryResponse } from "@/types/audit";

function AuditContent() {
  const { getAccessToken } = useAuth();
  const [entries, setEntries] = useState<AuditLogEntryResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken()
      .then((token) => listAuditLog(token))
      .then((page) => setEntries(page.items))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setError("Only Finance Admins can view the audit trail.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load audit log");
        }
      });
  }, [getAccessToken]);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">Audit trail</h1>
          <Card>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {!entries && !error ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : entries && entries.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No events recorded yet.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2 pr-4">Event</th>
                    <th className="py-2 pr-4">Aggregate</th>
                    <th className="py-2 pr-4">Occurred at</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {entries?.map((entry) => (
                    <tr key={entry.id}>
                      <td className="py-2 pr-4 font-mono">{entry.event_type}</td>
                      <td className="py-2 pr-4 font-mono text-xs text-slate-500">
                        {entry.aggregate_id.slice(0, 8)}…
                      </td>
                      <td className="py-2 pr-4">{new Date(entry.occurred_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function AuditPage() {
  return (
    <AuthGuard>
      <AuditContent />
    </AuthGuard>
  );
}
