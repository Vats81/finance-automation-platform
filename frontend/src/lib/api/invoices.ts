import { apiFetch } from "@/lib/api/client";
import { InvoiceResponse, PagedInvoicesResponse, SubmitInvoiceRequest } from "@/types/invoice";

export function listInvoices(token: string | null): Promise<PagedInvoicesResponse> {
  return apiFetch<PagedInvoicesResponse>("/invoices", token);
}

export function getInvoice(token: string | null, invoiceId: string): Promise<InvoiceResponse> {
  return apiFetch<InvoiceResponse>(`/invoices/${invoiceId}`, token);
}

export function submitInvoice(token: string | null, body: SubmitInvoiceRequest): Promise<InvoiceResponse> {
  return apiFetch<InvoiceResponse>("/invoices", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
