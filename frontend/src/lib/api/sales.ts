import { apiFetch } from "@/lib/api/client";
import { CreateSaleRequest, PagedSalesResponse, SaleResponse } from "@/types/sale";

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
  body: CreateSaleRequest
): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function recordSalePayment(
  token: string | null,
  businessId: string,
  saleId: string,
  amount: string
): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales/${saleId}/payments`, token, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}

export function voidSale(token: string | null, businessId: string, saleId: string): Promise<SaleResponse> {
  return apiFetch<SaleResponse>(`/businesses/${businessId}/sales/${saleId}/void`, token, {
    method: "POST",
  });
}
