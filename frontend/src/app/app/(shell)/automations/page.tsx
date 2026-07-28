"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { getNotifications } from "@/lib/api/notifications";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { NotificationsResponse } from "@/types/notifications";

const SEVERITY_TONE: Record<string, "danger" | "warning"> = {
  critical: "danger",
  warning: "warning",
};

export default function AutomationsPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [notifications, setNotifications] = useState<NotificationsResponse | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    getNotifications(getAccessToken(), currentBusinessId)
      .then(setNotifications)
      .catch(() => undefined);
  }, [currentBusinessId, getAccessToken]);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Notifications & Alerts</h1>
      <p className="mb-6 text-sm text-slate-500">
        Overdue payments and stock levels that need your attention, computed from your current data.
        Recurring, scheduled automation rules are coming in a later phase of this build.
      </p>

      <Card>
        {!notifications ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : notifications.count === 0 ? (
          <p className="text-sm text-slate-500">You&apos;re all caught up — no alerts right now.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {notifications.items.map((item) => (
              <li key={item.id} className="py-3 first:pt-0 last:pb-0">
                <Link href={item.link} className="flex items-center justify-between gap-3 hover:underline">
                  <span className="text-sm text-slate-800">{item.message}</span>
                  <Badge tone={SEVERITY_TONE[item.severity] ?? "neutral"}>{item.severity}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
