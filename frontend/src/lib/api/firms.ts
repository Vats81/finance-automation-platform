import { apiFetch } from "@/lib/api/client";
import { IdempotencyOptions, idempotencyHeaders } from "@/lib/idempotency";
import { BusinessResponse } from "@/types/business";
import { FirmAuditEvent, FirmClientResponse, FirmResponse, FirmRole, FirmStaffResponse } from "@/types/firm";

export function listMyFirms(token: string | null): Promise<FirmResponse[]> {
  return apiFetch<FirmResponse[]>("/firms", token);
}

export function createFirm(
  token: string | null,
  name: string,
  options?: IdempotencyOptions
): Promise<FirmResponse> {
  return apiFetch<FirmResponse>("/firms", token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify({ name }),
  });
}

export function listFirmClients(
  token: string | null,
  firmId: string,
  range?: { start_date?: string; end_date?: string }
): Promise<FirmClientResponse[]> {
  const params = new URLSearchParams();
  if (range?.start_date) params.set("start_date", range.start_date);
  if (range?.end_date) params.set("end_date", range.end_date);
  const query = params.toString();
  return apiFetch<FirmClientResponse[]>(`/firms/${firmId}/clients${query ? `?${query}` : ""}`, token);
}

export function addFirmClient(
  token: string | null,
  firmId: string,
  name: string,
  currency: string,
  options?: IdempotencyOptions
): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>(`/firms/${firmId}/clients`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify({ name, currency }),
  });
}

export function listFirmAuditEvents(token: string | null, firmId: string): Promise<FirmAuditEvent[]> {
  return apiFetch<FirmAuditEvent[]>(`/firms/${firmId}/audit-events?limit=50`, token);
}

export function releaseFirmClient(
  token: string | null,
  firmId: string,
  businessId: string
): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>(`/firms/${firmId}/clients/${businessId}/release`, token, {
    method: "POST",
  });
}

export function listFirmStaff(token: string | null, firmId: string): Promise<FirmStaffResponse[]> {
  return apiFetch<FirmStaffResponse[]>(`/firms/${firmId}/staff`, token);
}

export function inviteFirmStaff(
  token: string | null,
  firmId: string,
  body: { email: string; role: FirmRole }
): Promise<FirmStaffResponse> {
  return apiFetch<FirmStaffResponse>(`/firms/${firmId}/staff`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function changeFirmStaffRole(
  token: string | null,
  firmId: string,
  membershipId: string,
  role: FirmRole
): Promise<FirmStaffResponse> {
  return apiFetch<FirmStaffResponse>(`/firms/${firmId}/staff/${membershipId}`, token, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeFirmStaff(
  token: string | null,
  firmId: string,
  membershipId: string
): Promise<FirmStaffResponse> {
  return apiFetch<FirmStaffResponse>(`/firms/${firmId}/staff/${membershipId}/remove`, token, {
    method: "POST",
  });
}
