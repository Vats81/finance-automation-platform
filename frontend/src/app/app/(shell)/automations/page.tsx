"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { getNotifications } from "@/lib/api/notifications";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { NotificationsResponse } from "@/types/notifications";
import { useT } from "@/lib/i18n/LanguageProvider";

const SEVERITY_TONE: Record<string, "danger" | "warning"> = {
  critical: "danger",
  warning: "warning",
};

export default function AutomationsPage() {
  const { t, label } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [notifications, setNotifications] = useState<NotificationsResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!currentBusinessId) return;
    setNotifications(null);
    setLoadError(null);
    getNotifications(getAccessToken(), currentBusinessId)
      .then(setNotifications)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [currentBusinessId, getAccessToken, retryToken]);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">{t("top.notificationsTitle")}</h1>
      <p className="mb-6 text-sm text-slate-500">
        {t("s.overdue_payments_and_stock_levels")}
      </p>

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={() => setRetryToken((n) => n + 1)} />
        ) : !notifications ? (
          <p className="text-sm text-slate-500">{t("s.loading")}</p>
        ) : notifications.count === 0 ? (
          <p className="text-sm text-slate-500">{t("s.you_re_all_caught_up_no_alerts_rig")}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {notifications.items.map((item) => (
              <li key={item.id} className="py-3 first:pt-0 last:pb-0">
                <Link href={item.link} className="flex items-center justify-between gap-3 hover:underline">
                  <span className="text-sm text-slate-800">{item.message}</span>
                  <Badge tone={SEVERITY_TONE[item.severity] ?? "neutral"}>{label("severity", item.severity)}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
