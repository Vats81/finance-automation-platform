import { apiFetch } from "@/lib/api/client";
import { CreatePurchaseOrderRequest, PagedPurchaseOrdersResponse, PurchaseOrderResponse } from "@/types/purchaseOrder";

export function listPurchaseOrders(token: string | null): Promise<PagedPurchaseOrdersResponse> {
  return apiFetch<PagedPurchaseOrdersResponse>("/purchase-orders", token);
}

export function getPurchaseOrder(token: string | null, poId: string): Promise<PurchaseOrderResponse> {
  return apiFetch<PurchaseOrderResponse>(`/purchase-orders/${poId}`, token);
}

export function createPurchaseOrder(
  token: string | null,
  body: CreatePurchaseOrderRequest
): Promise<PurchaseOrderResponse> {
  return apiFetch<PurchaseOrderResponse>("/purchase-orders", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
