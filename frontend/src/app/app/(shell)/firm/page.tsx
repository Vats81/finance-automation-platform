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
import { useT } from "@/lib/i18n/LanguageProvider";

type Period = "all" | "month" | "year";

function periodRange(period: Period): { start_date?: string; end_date?: string } {
  const now = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  if (period === "month") return { start_date: iso(new Date(now.getFullYear(), now.getMonth(), 1)), end_date: iso(now) };
  if (period === "year") return { start_date: iso(new Date(now.getFullYear(), 0, 1)), end_date: iso(now) };
  return {};
}

export default function FirmClientsPage() {
  const { t, label, lang } = useT();
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
      setActionError(errorMessage(err, t("s.the_client_couldn_t_be_added")));
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
        t("x.releaseClient", { name: client.business.name })
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
      setActionError(errorMessage(err, t("s.the_client_couldn_t_be_released")));
    }
  }

  if (!currentFirm) {
    return <p className="text-sm text-slate-500">{t("s.you_are_not_part_of_an_accounting")}</p>;
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{currentFirm.name}</h1>
          <p className="text-sm text-slate-500">
            {t("firm.intro", { role: label("set.role", currentFirm.my_role) })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {firms.length > 1 && (
            <Select
              aria-label={t("s.select_firm")}
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
            aria-label={t("s.period")}
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
            className="max-w-[10rem]"
          >
            <option value="all">{t("dash.period.all_time")}</option>
            <option value="month">{t("dash.period.this_month")}</option>
            <option value="year">{t("dash.period.this_year")}</option>
          </Select>
        </div>
      </div>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      {canManage && (
        <Card className="mb-6">
          <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3">
            <label className="block flex-1 text-sm">
              <span className="mb-1 block font-medium">{t("s.add_a_client_business")}</span>
              <Input
                required
                maxLength={255}
                placeholder={t("s.client_or_company_name")}
                value={newClient}
                onChange={(e) => setNewClient(e.target.value)}
              />
            </label>
            <Button type="submit" disabled={isAdding}>
              {isAdding ? t("s.adding") : t("s.add_client")}
            </Button>
          </form>
        </Card>
      )}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={load} />
        ) : !clients ? (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        ) : clients.length === 0 ? (
          <p className="text-sm text-slate-500">
            {canManage ? t("x.noClientsAdd") : t("x.noClientsWait")}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-4">{t("s.client")}</th>
                  <th className="py-2 pr-4 text-right">{t("nav.sales")}</th>
                  <th className="py-2 pr-4 text-right">{t("nav.expenses")}</th>
                  <th className="py-2 pr-4 text-right">{t("s.profit")}</th>
                  <th className="py-2 pr-4 text-right">{t("s.owed_to_them")}</th>
                  <th className="py-2 pr-4">{t("s.last_activity")}</th>
                  <th className="py-2 pr-4">
                    <span className="sr-only">{t("set.team.actions")}</span>
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
                          <Badge tone="danger">{t("s.suspended")}</Badge>
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
                      {client.last_activity ? new Date(client.last_activity).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-US") : "—"}
                    </td>
                    <td className="flex gap-2 py-2 pr-4">
                      <Button
                        variant="secondary"
                        disabled={client.suspended}
                        onClick={() => openClient(client.business.id)}
                      >
                        {t("s.open")}
                      </Button>
                      {canManage && (
                        <Button variant="ghost" onClick={() => handleRelease(client)}>
                          {t("s.release")}
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
