"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiError } from "@/lib/api/client";
import { addFirmClient, listFirmClients, releaseFirmClient } from "@/lib/api/firms";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { detectCurrency, formatMoney } from "@/lib/format";
import { useSubmissionKey } from "@/lib/idempotency";
import { FirmClientResponse } from "@/types/firm";

type Period = "all" | "month" | "year";

function periodRange(period: Period): { start_date?: string; end_date?: string } {
  const now = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  if (period === "month") return { start_date: iso(new Date(now.getFullYear(), now.getMonth(), 1)), end_date: iso(now) };
  if (period === "year") return { start_date: iso(new Date(now.getFullYear(), 0, 1)), end_date: iso(now) };
  return {};
}

export default function FirmClientsPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentFirm, firms, setCurrentFirmId, setCurrentBusinessId, refresh } = useCurrentBusiness();
  const router = useRouter();
  const [clients, setClients] = useState<FirmClientResponse[] | null>(null);
  const [period, setPeriod] = useState<Period>("all");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [newClient, setNewClient] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const submission = useSubmissionKey();

  const canManage = currentFirm?.my_role === "owner" || currentFirm?.my_role === "admin";

  const load = useCallback(() => {
    if (!currentFirm) return;
    setLoadError(null);
    listFirmClients(getAccessToken(), currentFirm.id, periodRange(period))
      .then(setClients)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [currentFirm, getAccessToken, period]);

  useEffect(() => {
    setClients(null);
    load();
  }, [load]);

  async function handleAdd(event: FormEvent) {
    event.preventDefault();
    if (!currentFirm || !newClient.trim()) return;
    setIsAdding(true);
    setActionError(null);
    try {
      await addFirmClient(getAccessToken(), currentFirm.id, newClient.trim(), detectCurrency(), {
        idempotencyKey: submission.key(),
      });
      setNewClient("");
      submission.renew();
      await refresh(); // the new client joins the business switcher
      load();
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "idempotency_key_reused") submission.renew();
      setActionError(errorMessage(err, "The client couldn't be added."));
    } finally {
      setIsAdding(false);
    }
  }

  function openClient(businessId: string) {
    setCurrentBusinessId(businessId);
    router.push("/app/dashboard");
  }

  async function handleRelease(client: FirmClientResponse) {
    if (!currentFirm) return;
    if (
      !window.confirm(
        `Release "${client.business.name}"? It keeps all of its data and its own team, and your firm's staff lose access to it.`
      )
    ) {
      return;
    }
    setActionError(null);
    try {
      await releaseFirmClient(getAccessToken(), currentFirm.id, client.business.id);
      await refresh();
      load();
    } catch (err) {
      setActionError(errorMessage(err, "The client couldn't be released."));
    }
  }

  if (!currentFirm) {
    return <p className="text-sm text-slate-500">You are not part of an accounting firm yet.</p>;
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{currentFirm.name}</h1>
          <p className="text-sm text-slate-500">
            Your clients at a glance. You are {currentFirm.my_role === "admin" ? "an" : "a"} {currentFirm.my_role} of
            this firm.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {firms.length > 1 && (
            <Select
              aria-label="Select firm"
              value={currentFirm.id}
              onChange={(e) => setCurrentFirmId(e.target.value)}
              className="max-w-[12rem]"
            >
              {firms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </Select>
          )}
          <Select
            aria-label="Period"
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
            className="max-w-[10rem]"
          >
            <option value="all">All time</option>
            <option value="month">This month</option>
            <option value="year">This year</option>
          </Select>
        </div>
      </div>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      {canManage && (
        <Card className="mb-6">
          <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3">
            <label className="block flex-1 text-sm">
              <span className="mb-1 block font-medium">Add a client business</span>
              <Input
                required
                maxLength={255}
                placeholder="Client or company name"
                value={newClient}
                onChange={(e) => setNewClient(e.target.value)}
              />
            </label>
            <Button type="submit" disabled={isAdding}>
              {isAdding ? "Adding…" : "Add client"}
            </Button>
          </form>
        </Card>
      )}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={load} />
        ) : !clients ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : clients.length === 0 ? (
          <p className="text-sm text-slate-500">
            No clients yet.{canManage ? " Add your first client above." : " An owner or admin can add clients."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-4">Client</th>
                  <th className="py-2 pr-4 text-right">Sales</th>
                  <th className="py-2 pr-4 text-right">Expenses</th>
                  <th className="py-2 pr-4 text-right">Profit</th>
                  <th className="py-2 pr-4 text-right">Owed to them</th>
                  <th className="py-2 pr-4">Last activity</th>
                  <th className="py-2 pr-4">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {clients.map((client) => (
                  <tr key={client.business.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-4 font-medium">
                      {client.business.name}
                      {client.suspended && (
                        <span className="ml-2">
                          <Badge tone="danger">suspended</Badge>
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right">{formatMoney(client.total_revenue, client.business.currency)}</td>
                    <td className="py-2 pr-4 text-right">{formatMoney(client.total_expenses, client.business.currency)}</td>
                    <td
                      className={`py-2 pr-4 text-right ${Number(client.net_profit) < 0 ? "text-red-600" : ""}`}
                    >
                      {formatMoney(client.net_profit, client.business.currency)}
                    </td>
                    <td className="py-2 pr-4 text-right">{formatMoney(client.outstanding_receivables, client.business.currency)}</td>
                    <td className="py-2 pr-4 text-slate-500">
                      {client.last_activity ? new Date(client.last_activity).toLocaleDateString("en-US") : "—"}
                    </td>
                    <td className="flex gap-2 py-2 pr-4">
                      <Button
                        variant="secondary"
                        disabled={client.suspended}
                        onClick={() => openClient(client.business.id)}
                      >
                        Open
                      </Button>
                      {canManage && (
                        <Button variant="ghost" onClick={() => handleRelease(client)}>
                          Release
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
