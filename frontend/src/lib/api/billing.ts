import { apiFetch } from "@/lib/api/client";
import { BillingPortalSessionResponse, CheckoutSessionResponse, StartCheckoutSessionRequest } from "@/types/billing";

export function startCheckoutSession(
  token: string | null,
  businessId: string,
  body: StartCheckoutSessionRequest
): Promise<CheckoutSessionResponse> {
  return apiFetch<CheckoutSessionResponse>(`/businesses/${businessId}/billing/checkout-session`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function startBillingPortalSession(
  token: string | null,
  businessId: string
): Promise<BillingPortalSessionResponse> {
  return apiFetch<BillingPortalSessionResponse>(`/businesses/${businessId}/billing/portal-session`, token, {
    method: "POST",
  });
}
