"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { changeFirmPlan, getFirmBilling, openFirmBillingPortal, startFirmCheckout } from "@/lib/api/firms";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { FIRM_PLANS, FirmBillingResponse, FirmPlan } from "@/types/firm";

const PLAN_ORDER: FirmPlan[] = ["free", "growth", "practice"];

function Usage({ label, used, max }: { label: string; used: number; max: number }) {
  const percent = Math.min(100, (used / max) * 100);
  const full = used >= max;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className={full ? "text-amber-700" : "text-slate-600"}>
          {used} of {max}
        </span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${full ? "bg-amber-500" : "bg-brand-500"}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export default function FirmBillingPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentFirm, refresh } = useCurrentBusiness();
  const [billing, setBilling] = useState<FirmBillingResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isOwner = currentFirm?.my_role === "owner";

  const load = useCallback(() => {
    if (!currentFirm) return;
    setLoadError(null);
    getFirmBilling(getAccessToken(), currentFirm.id)
      .then(setBilling)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [currentFirm, getAccessToken]);

  useEffect(() => {
    setBilling(null);
    load();
  }, [load]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setActionError(null);
    try {
      await action();
    } catch (err) {
      setActionError(errorMessage(err, "That didn't work."));
      setBusy(false);
    }
  }

  const upgrade = (plan: FirmPlan) =>
    run(async () => {
      if (!currentFirm) return;
      const { checkout_url } = await startFirmCheckout(getAccessToken(), currentFirm.id, plan);
      window.location.href = checkout_url;
    });

  const manage = () =>
    run(async () => {
      if (!currentFirm) return;
      const { portal_url } = await openFirmBillingPortal(getAccessToken(), currentFirm.id);
      window.location.href = portal_url;
    });

  const chooseDirectly = (plan: FirmPlan) =>
    run(async () => {
      if (!currentFirm) return;
      await changeFirmPlan(getAccessToken(), currentFirm.id, plan);
      await refresh();
      load();
      setBusy(false);
    });

  if (!currentFirm) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Plan &amp; billing</h1>

      {loadError && <InlineError message={loadError} onRetry={load} />}
      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      {billing && (
        <div className="max-w-3xl space-y-6">
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{currentFirm.name}</h2>
              <Badge tone="success">{FIRM_PLANS[billing.plan].label} plan</Badge>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Usage label="Client businesses" used={billing.clients} max={billing.max_clients} />
              <Usage label="Staff" used={billing.staff} max={billing.max_staff} />
            </div>
            {(billing.clients >= billing.max_clients || billing.staff >= billing.max_staff) && (
              <p className="mt-4 text-sm text-amber-700">
                You&apos;ve reached a limit of this plan. Everything you have stays available; upgrade to add more.
              </p>
            )}
          </Card>

          <div className="grid gap-4 sm:grid-cols-3">
            {PLAN_ORDER.map((plan) => {
              const spec = FIRM_PLANS[plan];
              const current = plan === billing.plan;
              return (
                <Card key={plan} className={current ? "border-brand-500" : ""}>
                  <div className="font-semibold">{spec.label}</div>
                  <ul className="mt-2 space-y-1 text-sm text-slate-600">
                    <li>Up to {spec.maxClients} client businesses</li>
                    <li>Up to {spec.maxStaff} staff</li>
                  </ul>
                  <div className="mt-4">
                    {current ? (
                      <span className="text-sm text-slate-500">Your plan</span>
                    ) : !isOwner ? null : billing.billing_connected ? (
                      plan !== "free" && !billing.has_subscription ? (
                        <Button disabled={busy} onClick={() => upgrade(plan)}>
                          {busy ? "Redirecting…" : `Choose ${spec.label}`}
                        </Button>
                      ) : null
                    ) : (
                      <Button variant="secondary" disabled={busy} onClick={() => chooseDirectly(plan)}>
                        Switch to {spec.label}
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>

          {isOwner && billing.billing_connected && billing.has_subscription && (
            <Button disabled={busy} onClick={manage}>
              {busy ? "Redirecting…" : "Manage billing"}
            </Button>
          )}
          {!isOwner && <p className="text-xs text-slate-400">Only the firm&apos;s owner can change the plan.</p>}
          {!billing.billing_connected && (
            <p className="text-xs text-slate-400">
              Private beta: every plan is free and no payment is taken. Plans only set how many clients and staff
              the firm can have.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
