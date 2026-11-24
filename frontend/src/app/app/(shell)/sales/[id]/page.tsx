"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { getCustomer } from "@/lib/api/customers";
import {
  createInvoiceShareLink,
  downloadSaleInvoicePdf,
  getSale,
  recordSalePayment,
  revokeInvoiceShareLinks,
  voidSale,
} from "@/lib/api/sales";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import { invoiceMessage, whatsappLink, whatsappPhone } from "@/lib/whatsapp";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useSubmissionKey } from "@/lib/idempotency";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { SalePaymentStatus, SaleResponse } from "@/types/sale";
import { formatCurrency } from "@/lib/format";
import { isInterState, normalizeRate, splitTaxCents } from "@/lib/gst";

const STATUS_TONE: Record<SalePaymentStatus, "success" | "warning" | "neutral"> = {
  paid: "success",
  partially_paid: "warning",
  unpaid: "neutral",
};

export default function SaleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  const { t } = useT();
  const paymentKey = useSubmissionKey();
  const [sale, setSale] = useState<SaleResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    try {
      setSale(await getSale(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sale.loadFailed"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRecordPayment(event: FormEvent) {
    event.preventDefault();
    if (!currentBusinessId) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setSale(await recordSalePayment(token, currentBusinessId, id, paymentAmount, { idempotencyKey: paymentKey.key() }));
      setPaymentAmount("");
      paymentKey.renew();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sale.paymentFailed"));
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleDownloadInvoice() {
    if (!currentBusinessId || !sale) return;
    setIsDownloading(true);
    setError(null);
    try {
      await downloadSaleInvoicePdf(getAccessToken(), currentBusinessId, id, sale.invoice_number);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sale.downloadFailed"));
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleShareWhatsApp() {
    if (!currentBusinessId || !sale || !currentBusiness) return;
    // Open the tab now, inside the tap, so a phone browser does not block it; it is pointed at WhatsApp below.
    const popup = window.open("", "_blank");
    setIsSharing(true);
    setError(null);
    setNotice(null);
    try {
      const token = getAccessToken();
      const link = await createInvoiceShareLink(token, currentBusinessId, id);
      let customerName: string | null = null;
      let phone = "";
      if (sale.customer_id) {
        try {
          const customer = await getCustomer(token, currentBusinessId, sale.customer_id);
          customerName = customer.name;
          phone = whatsappPhone(customer.phone);
        } catch {
          // no customer details: the user picks the contact in WhatsApp
        }
      }
      const text = invoiceMessage(t, {
        customerName,
        businessName: currentBusiness.business.name,
        invoiceNumber: sale.invoice_number,
        invoiceDate: sale.invoice_date,
        total: formatCurrency(sale.total_amount),
        balance: formatCurrency(sale.outstanding_amount),
        url: link.url,
      });
      const target = whatsappLink(phone, text);
      if (popup) popup.location.href = target;
      else window.location.href = target;
    } catch (err) {
      popup?.close();
      setError(err instanceof Error ? err.message : t("sale.linkFailed"));
    } finally {
      setIsSharing(false);
    }
  }

  async function handleStopSharing() {
    if (!currentBusinessId) return;
    setError(null);
    setNotice(null);
    try {
      const result = await revokeInvoiceShareLinks(getAccessToken(), currentBusinessId, id);
      setNotice(
        result.revoked > 0
          ? t("sale.linksStopped")
          : t("sale.noLinks")
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sale.stopFailed"));
    }
  }

  async function handleVoid() {
    if (!currentBusinessId) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setSale(await voidSale(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sale.voidFailed"));
    } finally {
      setIsUpdating(false);
    }
  }

  if (!sale) {
    return (
      <div className="flex justify-center py-8">
        {error ? <p className="text-sm text-red-600">{error}</p> : <Spinner />}
      </div>
    );
  }

  const hasGst = (sale.gst_breakdown ?? []).length > 0;
  const interState = isInterState(currentBusiness?.business.state_code, sale.place_of_supply);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{sale.invoice_number}</h1>
          <p className="text-sm text-slate-500">{sale.invoice_date}</p>
        </div>
        <div className="flex items-center gap-2">
          {sale.status === "void" && <Badge tone="neutral">{t("sales.void")}</Badge>}
          <Badge tone={STATUS_TONE[sale.payment_status]}>{t(`sales.status.${sale.payment_status}` as MessageKey)}</Badge>
          <Button variant="secondary" onClick={handleDownloadInvoice} disabled={isDownloading}>
            {isDownloading ? t("common.preparing") : t("sale.download")}
          </Button>
          {sale.status !== "void" && (
            <Button onClick={handleShareWhatsApp} disabled={isSharing}>
              {isSharing ? t("common.preparing") : t("sale.sendWhatsApp")}
            </Button>
          )}
          {sale.status !== "void" && (
            <Link href={`/app/sales/${sale.id}/edit`}>
              <Button variant="secondary">{t("common.edit")}</Button>
            </Link>
          )}
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {notice && <p className="mb-4 text-sm text-green-700">{notice}</p>}
      {sale.status !== "void" && (
        <button
          type="button"
          onClick={handleStopSharing}
          className="mb-4 text-xs text-slate-500 underline hover:text-slate-700"
        >
          {t("sale.stopLinks")}
        </button>
      )}

      <Card className="mb-6 max-w-2xl">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-4">{t("common.description")}</th>
              <th className="py-2 pr-4">{t("sale.qty")}</th>
              <th className="py-2 pr-4">{t("sale.unitPrice")}</th>
              {hasGst && <th className="py-2 pr-4">{t("sale.gst")}</th>}
              <th className="py-2 pr-4">{t("sale.lineTotal")}</th>
            </tr>
          </thead>
          <tbody>
            {sale.line_items.map((item) => (
              <tr key={item.line_number} className="border-b border-slate-100 last:border-0">
                <td className="py-2 pr-4">{item.description}</td>
                <td className="py-2 pr-4">{item.quantity}</td>
                <td className="py-2 pr-4">{formatCurrency(item.unit_price)}</td>
                {hasGst && (
                  <td className="py-2 pr-4 text-slate-600">
                    {item.gst_rate !== null && item.gst_rate !== undefined ? `${normalizeRate(item.gst_rate)}%` : "—"}
                    {item.hsn_code ? <span className="block text-xs text-slate-400">{t("sale.hsn")} {item.hsn_code}</span> : null}
                  </td>
                )}
                <td className="py-2 pr-4">{formatCurrency(item.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 space-y-1 border-t border-slate-200 pt-4 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">{t("sale.subtotal")}</span>
            <span>{formatCurrency(sale.subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">{t("sale.discount")}</span>
            <span>-{formatCurrency(sale.discount)}</span>
          </div>
          {hasGst ? (
            <>
              {(sale.gst_breakdown ?? [])
                .filter((g) => Number(g.rate) > 0)
                .map((g) => (
                  <div key={g.rate} className="flex justify-between text-slate-600">
                    <span>
                      {t("sale.gstOn", { rate: normalizeRate(g.rate), amount: formatCurrency(g.taxable_value) })}
                    </span>
                    <span>
                      {interState
                        ? `IGST ${formatCurrency(g.tax)}`
                        : `CGST ${formatCurrency(splitTaxCents(Math.round(Number(g.tax) * 100), false).cgst / 100)} + SGST ${formatCurrency(
                            splitTaxCents(Math.round(Number(g.tax) * 100), false).sgst / 100
                          )}`}
                    </span>
                  </div>
                ))}
              <div className="flex justify-between">
                <span className="text-slate-500">{t("sale.totalGst")}</span>
                <span>{formatCurrency(sale.tax)}</span>
              </div>
            </>
          ) : (
            <div className="flex justify-between">
              <span className="text-slate-500">{t("sale.tax")}</span>
              <span>{formatCurrency(sale.tax)}</span>
            </div>
          )}
          <div className="flex justify-between font-semibold">
            <span>{t("common.total")}</span>
            <span>{formatCurrency(sale.total_amount)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">{t("sale.received")}</span>
            <span>{formatCurrency(sale.amount_received)}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span>{t("sale.outstanding")}</span>
            <span>{formatCurrency(sale.outstanding_amount)}</span>
          </div>
        </div>
      </Card>

      {sale.status !== "void" && (
        <Card className="max-w-2xl space-y-4">
          {sale.payment_status !== "paid" && (
            <form onSubmit={handleRecordPayment} className="flex items-end gap-2">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">{t("sale.recordPayment")}</label>
                <Input
                  required
                  type="number"
                  step="0.01"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={isUpdating}>
                {t("sale.record")}
              </Button>
            </form>
          )}
          <Button variant="danger" disabled={isUpdating} onClick={handleVoid}>
            {t("sale.void")}
          </Button>
        </Card>
      )}
    </div>
  );
}
