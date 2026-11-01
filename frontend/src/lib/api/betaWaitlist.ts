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
  invitation_sent_at: string | null;
}

export interface InvitationDraft {
  to: string;
  subject: string;
  body: string;
  is_firm: boolean;
  already_sent_at: string | null;
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


export function getInvitationDraft(token: string | null, entryId: string): Promise<InvitationDraft> {
  return apiFetch<InvitationDraft>(`/admin/beta-waitlist/${entryId}/invitation-draft`, token);
}

export function sendInvitationEmail(
  token: string | null,
  entryId: string,
  body: { subject: string; body: string; resend: boolean }
): Promise<WaitlistEntry> {
  return apiFetch<WaitlistEntry>(`/admin/beta-waitlist/${entryId}/send-invitation`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
