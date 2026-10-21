"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import {
  listBusinessesOverview,
  purgeBusiness,
  reactivateBusiness,
  suspendBusiness,
} from "@/lib/api/admin";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { BusinessesOverviewResponse } from "@/types/admin";

const PAGE_SIZE = 20;

const PLAN_TONE: Record<string, "neutral" | "success"> = {
  free: "neutral",
  starter: "success",
  pro: "success",
};

const STATUS_TONE: Record<string, "success" | "danger"> = {
  active: "success",
  suspended: "danger",
};

export default function AdminBusinessesPage() {
  const { getAccessToken } = useLocalAuth();
  const [page, setPage] = useState<BusinessesOverviewResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = () => {
    listBusinessesOverview(getAccessToken(), { offset, limit: PAGE_SIZE })
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

  async function handleToggleStatus(businessId: string, currentStatus: string) {
    setPendingId(businessId);
    setActionError(null);
    try {
      if (currentStatus === "active") {
        await suspendBusiness(getAccessToken(), businessId);
      } else {
        await reactivateBusiness(getAccessToken(), businessId);
      }
      refresh();
    } catch (err) {
      // Previously swallowed: a rejected suspend/reactivate just looked
      // like the button did nothing.
      setActionError(errorMessage(err, "That change couldn't be saved."));
    } finally {
      setPendingId(null);
    }
  }

  async function handlePurge(businessId: string, name: string) {
    const typed = window.prompt(
      `This permanently deletes "${name}" and ALL of its sales, purchases, expenses, products, customers, vendors and team memberships. It cannot be undone.

Type the business name to confirm:`
    );
    if (typed === null) return;
    setPendingId(businessId);
    setActionError(null);
    try {
      await purgeBusiness(getAccessToken(), businessId, typed);
      refresh();
    } catch (err) {
      setActionError(errorMessage(err, "The business couldn't be deleted."));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Businesses</h1>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={retry} />
        ) : !page ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : page.items.length === 0 ? (
          <p className="text-sm text-slate-500">No businesses yet.</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Plan</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium">Members</th>
                  <th className="py-2 pr-4 font-medium">Owner</th>
                  <th className="py-2 pr-4 font-medium">Created</th>
                  <th className="py-2 pr-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((business) => (
                  <tr key={business.id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{business.name}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={PLAN_TONE[business.plan] ?? "neutral"}>{business.plan}</Badge>
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone={STATUS_TONE[business.status] ?? "success"}>{business.status}</Badge>
                    </td>
                    <td className="py-2 pr-4">{business.member_count}</td>
                    <td className="py-2 pr-4">{business.owner_email}</td>
                    <td className="py-2 pr-4">
                      {new Date(business.created_at).toLocaleDateString("en-US")}
                    </td>
                    <td className="flex gap-2 py-2 pr-4">
                      <Button
                        variant={business.status === "active" ? "danger" : "secondary"}
                        disabled={pendingId === business.id}
                        onClick={() => handleToggleStatus(business.id, business.status)}
                      >
                        {business.status === "active" ? "Suspend" : "Reactivate"}
                      </Button>
                      <Button
                        variant="danger"
                        disabled={pendingId === business.id}
                        onClick={() => handlePurge(business.id, business.name)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
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
