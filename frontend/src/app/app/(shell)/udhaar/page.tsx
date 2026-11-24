"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getReceivables } from "@/lib/api/sales";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";
import { reminderMessage, whatsappLink, whatsappPhone } from "@/lib/whatsapp";
import { ReceivableCustomer, ReceivablesResponse } from "@/types/sale";

export default function UdhaarPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  const { t } = useT();
  const [data, setData] = useState<ReceivablesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    getReceivables(getAccessToken(), currentBusinessId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : t("udhaar.loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken]);

  const business = currentBusiness?.business;

  function remind(row: ReceivableCustomer) {
    const text = reminderMessage(t, {
      customerName: row.name,
      businessName: business?.name ?? "",
      amount: formatCurrency(row.outstanding),
      invoiceNumbers: row.invoices.map((i) => i.invoice_number),
      upiId: business?.upi_id,
    });
    window.open(whatsappLink(whatsappPhone(row.phone), text), "_blank");
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t("udhaar.title")}</h1>
          <p className="text-sm text-slate-500">{t("udhaar.subtitle")}</p>
        </div>
        <Link href="/app/sales/quick">
          <Button>{t("sales.quick")}</Button>
        </Link>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {!data && !error && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}

      {data && (
        <>
          <Card className="mb-4 max-w-2xl">
            <p className="text-sm text-slate-500">{t("udhaar.toCollect")}</p>
            <p className="text-3xl font-semibold">{formatCurrency(data.total_outstanding)}</p>
          </Card>

          {data.customers.length === 0 ? (
            <Card className="max-w-2xl">
              <p className="text-sm text-slate-600">{t("udhaar.nobody")}</p>
            </Card>
          ) : (
            <div className="max-w-2xl space-y-3">
              {data.customers.map((row) => {
                const key = row.customer_id ?? "walk-in";
                const isOpen = open === key;
                const count = row.invoices.length;
                return (
                  <Card key={key}>
                    <div className="flex items-center justify-between gap-3">
                      <button
                        type="button"
                        className="min-w-0 flex-1 text-left"
                        onClick={() => setOpen(isOpen ? null : key)}
                        aria-expanded={isOpen}
                      >
                        <p className="truncate font-medium">
                          {row.customer_id ? row.name : t("udhaar.walkIn")}
                        </p>
                        <p className="text-xs text-slate-500">
                          {count === 1 ? t("udhaar.invoice", { n: count }) : t("udhaar.invoices", { n: count })}
                          {row.days_overdue > 0 ? ` · ${t("udhaar.late", { n: row.days_overdue })}` : ""}
                        </p>
                      </button>
                      <div className="text-right">
                        <p className="font-semibold">{formatCurrency(row.outstanding)}</p>
                        {row.customer_id && (
                          <button
                            type="button"
                            className="mt-1 text-sm font-medium text-green-700 underline"
                            onClick={() => remind(row)}
                          >
                            {t("udhaar.remind")}
                          </button>
                        )}
                      </div>
                    </div>
                    {isOpen && (
                      <ul className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">
                        {row.invoices.map((inv) => (
                          <li key={inv.sale_id} className="flex justify-between">
                            <Link href={`/app/sales/${inv.sale_id}`} className="text-brand-700 hover:underline">
                              {inv.invoice_number}
                              <span className="ml-2 text-xs text-slate-500">{inv.invoice_date}</span>
                            </Link>
                            <span>{formatCurrency(inv.outstanding)}</span>
                          </li>
                        ))}
                        {!row.phone && row.customer_id && (
                          <li className="pt-1 text-xs text-slate-500">{t("udhaar.noPhone")}</li>
                        )}
                      </ul>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
