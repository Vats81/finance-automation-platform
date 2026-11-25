"use client";

import { useParams } from "next/navigation";
import { useEffect } from "react";
import { useT } from "@/lib/i18n/LanguageProvider";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** The page behind an invoice link a business sends to a customer: it opens the invoice PDF. */
export default function SharedInvoicePage() {
  const { token } = useParams<{ token: string }>();
  const { t } = useT();
  const pdfUrl = `${API_BASE_URL}/api/v1/public/invoices/${encodeURIComponent(token)}`;

  useEffect(() => {
    window.location.replace(pdfUrl);
  }, [pdfUrl]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <p className="text-center text-sm text-slate-600">
        {t("share.opening")}{" "}
        <a href={pdfUrl} className="text-brand-600 underline">
          {t("share.tap")}
        </a>
      </p>
    </div>
  );
}
