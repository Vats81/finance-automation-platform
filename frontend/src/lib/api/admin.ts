import { apiFetch } from "@/lib/api/client";
import {
  BusinessesOverviewResponse,
  ContactRequestsResponse,
  PlatformStats,
  UsersOverviewResponse,
} from "@/types/admin";

export function listBusinessesOverview(
  token: string | null,
  range?: { offset?: number; limit?: number }
): Promise<BusinessesOverviewResponse> {
  const params = new URLSearchParams();
  if (range?.offset !== undefined) params.set("offset", String(range.offset));
  if (range?.limit !== undefined) params.set("limit", String(range.limit));
  const query = params.toString();
  return apiFetch<BusinessesOverviewResponse>(`/admin/businesses${query ? `?${query}` : ""}`, token);
}

export function listUsersOverview(
  token: string | null,
  range?: { offset?: number; limit?: number }
): Promise<UsersOverviewResponse> {
  const params = new URLSearchParams();
  if (range?.offset !== undefined) params.set("offset", String(range.offset));
  if (range?.limit !== undefined) params.set("limit", String(range.limit));
  const query = params.toString();
  return apiFetch<UsersOverviewResponse>(`/admin/users${query ? `?${query}` : ""}`, token);
}

export function getPlatformStats(token: string | null): Promise<PlatformStats> {
  return apiFetch<PlatformStats>("/admin/stats", token);
}

export function suspendBusiness(token: string | null, businessId: string): Promise<void> {
  return apiFetch<void>(`/admin/businesses/${businessId}/suspend`, token, { method: "POST" });
}

export function reactivateBusiness(token: string | null, businessId: string): Promise<void> {
  return apiFetch<void>(`/admin/businesses/${businessId}/reactivate`, token, { method: "POST" });
}

export function deactivateUser(token: string | null, userId: string): Promise<void> {
  return apiFetch<void>(`/admin/users/${userId}/deactivate`, token, { method: "POST" });
}

export function setTemporaryPassword(
  token: string | null,
  userId: string
): Promise<{ temporary_password: string }> {
  return apiFetch<{ temporary_password: string }>(`/admin/users/${userId}/temporary-password`, token, {
    method: "POST",
  });
}

export function reactivateUser(token: string | null, userId: string): Promise<void> {
  return apiFetch<void>(`/admin/users/${userId}/reactivate`, token, { method: "POST" });
}

export function purgeBusiness(
  token: string | null,
  businessId: string,
  confirmName: string
): Promise<void> {
  return apiFetch<void>(
    `/admin/businesses/${businessId}?confirm_name=${encodeURIComponent(confirmName)}`,
    token,
    { method: "DELETE" }
  );
}

export function deleteUser(token: string | null, userId: string, confirmEmail: string): Promise<void> {
  return apiFetch<void>(
    `/admin/users/${userId}?confirm_email=${encodeURIComponent(confirmEmail)}`,
    token,
    { method: "DELETE" }
  );
}

export function deleteContactRequest(token: string | null, requestId: string): Promise<void> {
  return apiFetch<void>(`/admin/contact-requests/${requestId}`, token, { method: "DELETE" });
}

export function listContactRequests(token: string | null): Promise<ContactRequestsResponse> {
  return apiFetch<ContactRequestsResponse>("/admin/contact-requests", token);
}
