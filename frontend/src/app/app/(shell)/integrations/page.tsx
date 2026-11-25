"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { getIntegrationsStatus } from "@/lib/api/integrations";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { IntegrationsStatusResponse, ProviderStatus } from "@/types/integrations";
import { useT } from "@/lib/i18n/LanguageProvider";

const COMING_LATER = ["QuickBooks", "Zoho Books", "Tally", "Live Google Sheets sync"];

function StatusCard({ name, status }: { name: string; status: ProviderStatus }) {
  const { t } = useT();
  return (
    <div className="rounded-md border border-slate-200 p-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-slate-900">{name}</span>
        <Badge tone={status.connected ? (status.limited ? "warning" : "success") : "neutral"}>
          {status.connected ? (status.limited ? t("s.limited") : t("s.connected")) : t("s.not_configured")}
        </Badge>
      </div>
      <p className="text-xs text-slate-500">{status.detail}</p>
    </div>
  );
}

export default function IntegrationsPage() {
  const { t } = useT();
  const { getAccessToken } = useLocalAuth();
  const [status, setStatus] = useState<IntegrationsStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    setStatus(null);
    setLoadError(null);
    getIntegrationsStatus(getAccessToken())
      .then(setStatus)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [getAccessToken, retryToken]);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">{t("nav.integrations")}</h1>
      <p className="mb-6 text-sm text-slate-500">
        {t("s.see_which_services_this_app_is_act")}
      </p>

      <Card className="mb-6">
        <h2 className="mb-4 text-sm font-semibold">{t("s.connected_services")}</h2>
        {loadError ? (
          <InlineError message={loadError} onRetry={() => setRetryToken((n) => n + 1)} />
        ) : status ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <StatusCard name={t("integ.email")} status={status.email} />
            <StatusCard name={t("integ.whatsapp")} status={status.whatsapp} />
            <StatusCard name={t("integ.ai")} status={status.ai_assistant} />
            <StatusCard name={t("integ.storage")} status={status.document_storage} />
            <StatusCard name={t("integ.billing")} status={status.billing} />
          </div>
        ) : (
          <p className="text-sm text-slate-500">{t("s.loading")}</p>
        )}
      </Card>

      <Card className="mb-6">
        <h2 className="mb-4 text-sm font-semibold">{t("s.move_your_data")}</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Link
            href="/app/data-upload"
            className="rounded-md border border-slate-200 p-4 hover:border-brand-400 hover:bg-slate-50"
          >
            <div className="text-sm font-medium text-slate-900">{t("s.import_from_csv")}</div>
            <p className="mt-1 text-xs text-slate-500">
              {t("s.bring_in_customers_vendors_product")}
            </p>
          </Link>
          <Link
            href="/app/reports"
            className="rounded-md border border-slate-200 p-4 hover:border-brand-400 hover:bg-slate-50"
          >
            <div className="text-sm font-medium text-slate-900">{t("s.export_as_csv_or_pdf")}</div>
            <p className="mt-1 text-xs text-slate-500">
              {t("s.download_your_profit_loss_report_t")}
            </p>
          </Link>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">{t("s.coming_later")}</h2>
        <ul className="flex flex-wrap gap-2">
          {COMING_LATER.map((name) => (
            <li key={name}>
              <Badge tone="neutral">{name}</Badge>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
