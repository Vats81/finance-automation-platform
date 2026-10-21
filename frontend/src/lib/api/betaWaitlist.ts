import { apiFetch } from "@/lib/api/client";

export type WaitlistStatus =
  | "interested"
  | "qualified"
  | "waiting_for_checks"
  | "invited"
  | "onboarded"
  | "paused";

export interface JoinWaitlistRequest {
  name: string;
  work_email: string;
  business_name?: string;
  business_type?: string;
  bookkeeping_method?: string;
  reporting_problem?: string;
  weekly_feedback_ok: boolean;
  acknowledged: boolean;
  // Honeypot — always empty from the real form.
  website?: string;
}

export interface WaitlistEntry {
  id: string;
  name: string;
  work_email: string;
  business_name: string | null;
  business_type: string | null;
  bookkeeping_method: string | null;
  reporting_problem: string | null;
  weekly_feedback_ok: boolean;
  status: WaitlistStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// Public endpoint: no token. Registers interest only; it creates no account.
export function joinWaitlist(body: JoinWaitlistRequest): Promise<{ received: boolean }> {
  return apiFetch<{ received: boolean }>("/beta-waitlist", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listWaitlist(token: string | null): Promise<WaitlistEntry[]> {
  return apiFetch<WaitlistEntry[]>("/admin/beta-waitlist", token);
}

export function updateWaitlistEntry(
  token: string | null,
  entryId: string,
  body: { status?: WaitlistStatus; notes?: string }
): Promise<WaitlistEntry> {
  return apiFetch<WaitlistEntry>(`/admin/beta-waitlist/${entryId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteWaitlistEntry(token: string | null, entryId: string): Promise<void> {
  return apiFetch<void>(`/admin/beta-waitlist/${entryId}`, token, { method: "DELETE" });
}
