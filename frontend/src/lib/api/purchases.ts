import { apiFetch } from "@/lib/api/client";
import { IdempotencyOptions, idempotencyHeaders } from "@/lib/idempotency";
import {
  CreatePurchaseRequest,
  PagedPurchasesResponse,
  PurchaseResponse,
  UpdatePurchaseRequest,
} from "@/types/purchase";

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
  body: CreatePurchaseRequest,
  options?: IdempotencyOptions
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify(body),
  });
}

export function updatePurchase(
  token: string | null,
  businessId: string,
  purchaseId: string,
  body: UpdatePurchaseRequest
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases/${purchaseId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function recordPurchasePayment(
  token: string | null,
  businessId: string,
  purchaseId: string,
  amount: string,
  options?: IdempotencyOptions
): Promise<PurchaseResponse> {
  return apiFetch<PurchaseResponse>(`/businesses/${businessId}/purchases/${purchaseId}/payments`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
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
