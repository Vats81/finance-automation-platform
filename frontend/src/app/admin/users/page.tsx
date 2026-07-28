"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { deactivateUser, listUsersOverview, reactivateUser } from "@/lib/api/admin";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { UsersOverviewResponse } from "@/types/admin";

const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const { getAccessToken, user: currentAdmin } = useLocalAuth();
  const [page, setPage] = useState<UsersOverviewResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const refresh = () => {
    listUsersOverview(getAccessToken(), { offset, limit: PAGE_SIZE })
      .then(setPage)
      .catch(() => undefined);
  };

  useEffect(refresh, [getAccessToken, offset]);

  async function handleToggleActive(userId: string, isActive: boolean) {
    setPendingId(userId);
    try {
      if (isActive) {
        await deactivateUser(getAccessToken(), userId);
      } else {
        await reactivateUser(getAccessToken(), userId);
      }
      refresh();
    } catch {
      // no-op — same "table just doesn't update" fallback as the
      // businesses page; a real toast is out of scope for this slice
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Users</h1>

      <Card>
        {!page ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : page.items.length === 0 ? (
          <p className="text-sm text-slate-500">No users yet.</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Verified</th>
                  <th className="py-2 pr-4 font-medium">Active</th>
                  <th className="py-2 pr-4 font-medium">Created</th>
                  <th className="py-2 pr-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((user) => {
                  const isSelf = user.id === currentAdmin?.id;
                  return (
                    <tr key={user.id} className="border-b border-slate-100">
                      <td className="py-2 pr-4">{user.display_name}</td>
                      <td className="py-2 pr-4">{user.email}</td>
                      <td className="py-2 pr-4">
                        <Badge tone={user.is_email_verified ? "success" : "warning"}>
                          {user.is_email_verified ? "Verified" : "Unverified"}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">
                        <Badge tone={user.is_active ? "success" : "neutral"}>
                          {user.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">
                        {new Date(user.created_at).toLocaleDateString("en-US")}
                      </td>
                      <td className="py-2 pr-4">
                        {!isSelf && (
                          <Button
                            variant={user.is_active ? "danger" : "secondary"}
                            disabled={pendingId === user.id}
                            onClick={() => handleToggleActive(user.id, user.is_active)}
                          >
                            {user.is_active ? "Deactivate" : "Reactivate"}
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
              <span>
                Showing {page.offset + 1}–{Math.min(page.offset + page.items.length, page.total)} of{" "}
                {page.total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  disabled={offset + PAGE_SIZE >= page.total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
