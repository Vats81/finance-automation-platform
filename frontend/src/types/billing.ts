import { BusinessPlan } from "@/types/business";

export interface StartCheckoutSessionRequest {
  plan: BusinessPlan;
}

export interface CheckoutSessionResponse {
  checkout_url: string;
}

export interface BillingPortalSessionResponse {
  portal_url: string;
}
