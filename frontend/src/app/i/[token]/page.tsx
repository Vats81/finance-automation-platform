"use client";

import { useParams } from "next/navigation";
import { useEffect } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** The page behind an invoice link a business sends to a customer: it opens the invoice PDF. */
export default function SharedInvoicePage() {
  const { token } = useParams<{ token: string }>();
  const pdfUrl = `${API_BASE_URL}/api/v1/public/invoices/${encodeURIComponent(token)}`;

  useEffect(() => {
    window.location.replace(pdfUrl);
  }, [pdfUrl]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <p className="text-center text-sm text-slate-600">
        Opening your invoice…{" "}
        <a href={pdfUrl} className="text-brand-600 underline">
          Tap here if it does not open
        </a>
      </p>
    </div>
  );
}
