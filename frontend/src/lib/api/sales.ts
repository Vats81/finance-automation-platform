import { ApiError, apiFetch } from "@/lib/api/client";
import { IdempotencyOptions, idempotencyHeaders } from "@/lib/idempotency";
import { CreateSaleRequest, PagedSalesResponse, SaleResponse, UpdateSaleRequest } from "@/types/sale";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function listSales(token: string | null, businessId: string): Promise<PagedSalesResponse> {
  return apiFetch<PagedSalesResponse>(`/businesses/${businessId}/sales`, token);
}

export function listOutstandingSales(token: string | null, businessId: string): Promise<SaleResponse[]> {
  return apiFetch<SaleResponse[]>(`/businesses/${businessId}/sales/outstanding`, token);
}

export function getSale(token: string | null, businessId: string, saleId: string): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales/${saleId}`, token);
}

export function createSale(
  token: string | null,
  businessId: string,
  body: CreateSaleRequest,
  options?: IdempotencyOptions
): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify(body),
  });
}

export function updateSale(
  token: string | null,
  businessId: string,
  saleId: string,
  body: UpdateSaleRequest
): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales/${saleId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function recordSalePayment(
  token: string | null,
  businessId: string,
  saleId: string,
  amount: string,
  options?: IdempotencyOptions
): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales/${saleId}/payments`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify({ amount }),
  });
}

export function voidSale(token: string | null, businessId: string, saleId: string): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales/${saleId}/void`, token, {
    method: "POST",
  });
}

/** The printable invoice (a GST tax invoice when the lines carry GST rates), saved as a PDF. */
export async function downloadSaleInvoicePdf(
  token: string | null,
  businessId: string,
  saleId: string,
  invoiceNumber: string
): Promise<void> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/api/v1/businesses/${businessId}/sales/${saleId}/invoice-pdf`, {
    headers,
  });
  if (!response.ok) {
    throw new ApiError(response.statusText, response.status, "unknown_error");
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `invoice-${invoiceNumber.replace(/[^A-Za-z0-9_-]/g, "-")}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
