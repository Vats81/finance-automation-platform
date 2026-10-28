"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import {
  deactivateUser,
  deleteUser,
  listUsersOverview,
  reactivateUser,
  setTemporaryPassword,
} from "@/lib/api/admin";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { UsersOverviewResponse } from "@/types/admin";

const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const { getAccessToken, user: currentAdmin } = useLocalAuth();
  const [page, setPage] = useState<UsersOverviewResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [temporary, setTemporary] = useState<{ email: string; password: string } | null>(null);

  const refresh = () => {
    listUsersOverview(getAccessToken(), { offset, limit: PAGE_SIZE })
      .then((res) => {
        setPage(res);
        setLoadError(null);
      })
      .catch((err) => setLoadError(errorMessage(err)));
  };

  const retry = () => {
    setLoadError(null);
    setPage(null);
    refresh();
  };

  useEffect(refresh, [getAccessToken, offset]);

  async function handleToggleActive(userId: string, isActive: boolean) {
    setPendingId(userId);
    setActionError(null);
    try {
      if (isActive) {
        await deactivateUser(getAccessToken(), userId);
      } else {
        await reactivateUser(getAccessToken(), userId);
      }
      refresh();
    } catch (err) {
      // Previously swallowed: a rejected deactivate/reactivate (e.g. the
      // server refusing to deactivate yourself) just looked like the
      // button did nothing.
      setActionError(errorMessage(err, "That change couldn't be saved."));
    } finally {
      setPendingId(null);
    }
  }

  async function handleTemporaryPassword(userId: string, email: string) {
    if (
      !window.confirm(
        `Set a new temporary password for ${email}? Their current password stops working. You will see the new one once, to pass on to them.`
      )
    ) {
      return;
    }
    setPendingId(userId);
    setActionError(null);
    setTemporary(null);
    try {
      const res = await setTemporaryPassword(getAccessToken(), userId);
      setTemporary({ email, password: res.temporary_password });
    } catch (err) {
      setActionError(errorMessage(err, "The password couldn't be reset."));
    } finally {
      setPendingId(null);
    }
  }

  async function handleDelete(userId: string, email: string) {
    const typed = window.prompt(
      `This permanently deletes the account ${email}. Delete any business they own first. It cannot be undone.

Type their email to confirm:`
    );
    if (typed === null) return;
    setPendingId(userId);
    setActionError(null);
    try {
      await deleteUser(getAccessToken(), userId, typed);
      refresh();
    } catch (err) {
      setActionError(errorMessage(err, "The user couldn't be deleted."));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Users</h1>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      {temporary && (
        <Card className="mb-4 border-amber-300 bg-amber-50">
          <p className="text-sm">
            New temporary password for <strong>{temporary.email}</strong>. This is shown once. Pass it to them
            and ask them to sign in and change it.
          </p>
          <p className="mt-2 select-all rounded bg-white px-3 py-2 font-mono text-sm">{temporary.password}</p>
          <Button variant="secondary" className="mt-3" onClick={() => setTemporary(null)}>
            Done, hide it
          </Button>
        </Card>
      )}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={retry} />
        ) : !page ? (
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
                      <td className="flex gap-2 py-2 pr-4">
                        {!isSelf && (
                          <>
                            <Button
                              variant={user.is_active ? "danger" : "secondary"}
                              disabled={pendingId === user.id}
                              onClick={() => handleToggleActive(user.id, user.is_active)}
                            >
                              {user.is_active ? "Deactivate" : "Reactivate"}
                            </Button>
                            <Button
                              variant="secondary"
                              disabled={pendingId === user.id}
                              onClick={() => handleTemporaryPassword(user.id, user.email)}
                            >
                              Reset password
                            </Button>
                            <Button
                              variant="danger"
                              disabled={pendingId === user.id}
                              onClick={() => handleDelete(user.id, user.email)}
                            >
                              Delete
                            </Button>
                          </>
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
