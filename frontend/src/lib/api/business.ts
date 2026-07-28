import { apiFetch } from "@/lib/api/client";
import {
  BusinessResponse,
  ChangePlanRequest,
  CompleteOnboardingRequest,
  MyBusinessResponse,
  RegisterBusinessRequest,
} from "@/types/business";

export function registerBusiness(token: string | null, body: RegisterBusinessRequest): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>("/businesses", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listMyBusinesses(token: string | null): Promise<MyBusinessResponse[]> {
  return apiFetch<MyBusinessResponse[]>("/businesses", token);
}

export function getBusiness(token: string | null, businessId: string): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>(`/businesses/${businessId}`, token);
}

export function completeOnboarding(
  token: string | null,
  businessId: string,
  body: CompleteOnboardingRequest
): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>(`/businesses/${businessId}/onboarding`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function changeBusinessPlan(
  token: string | null,
  businessId: string,
  body: ChangePlanRequest
): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>(`/businesses/${businessId}/plan`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
