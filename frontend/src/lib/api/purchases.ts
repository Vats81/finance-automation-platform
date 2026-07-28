import { apiFetch } from "@/lib/api/client";
import { CreatePurchaseRequest, PagedPurchasesResponse, PurchaseResponse } from "@/types/purchase";

export function listPurchases(token: string | null, businessId: string): Promise<PagedPurchasesResponse> {
  return apiFetch<PagedPurchasesResponse>(`/businesses/${businessId}/purchases`, token);
}

export function listOutstandingPurchases(
  token: string | null,
  businessId: string
): Promise<PurchaseResponse[]> {
  return apiFetch<PurchaseResponse[]>(`/businesses/${businessId}/purchases/outstanding`, token);
}

export function getPurchase(
  token: string | null,
  businessId: string,
  purchaseId: string
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases/${purchaseId}`, token);
}

export function createPurchase(
  token: string | null,
  businessId: string,
  body: CreatePurchaseRequest
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function recordPurchasePayment(
  token: string | null,
  businessId: string,
  purchaseId: string,
  amount: string
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases/${purchaseId}/payments`, token, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}

export function voidPurchase(
  token: string | null,
  businessId: string,
  purchaseId: string
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases/${purchaseId}/void`, token, {
    method: "POST",
  });
}
