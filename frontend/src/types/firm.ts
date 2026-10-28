import { BusinessResponse } from "@/types/business";

export type FirmRole = "owner" | "admin" | "accountant" | "viewer";
export type FirmStatus = "active" | "suspended";

export const FIRM_ROLES: FirmRole[] = ["owner", "admin", "accountant", "viewer"];
// The roles a person can be invited as or changed to: the Owner role is never granted.
export const ASSIGNABLE_FIRM_ROLES: FirmRole[] = ["admin", "accountant", "viewer"];

export interface FirmResponse {
  id: string;
  name: string;
  status: FirmStatus;
  my_role: FirmRole;
  created_at: string;
}

export interface FirmStaffResponse {
  membership_id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: FirmRole;
  status: "active" | "removed";
}

export interface FirmClientResponse {
  business: BusinessResponse;
  suspended: boolean;
  total_revenue: string;
  total_expenses: string;
  net_profit: string;
  outstanding_receivables: string;
  last_activity: string | null;
}

export interface FirmAuditEvent {
  id: string;
  actor_user_id: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  status_code: number;
  occurred_at: string;
}
