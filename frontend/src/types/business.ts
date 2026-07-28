export type BusinessRole = "owner" | "admin" | "accountant" | "viewer";
export type BusinessStatus = "active" | "suspended";
export type BusinessPlan = "free" | "starter" | "pro";
export type MembershipStatus = "active" | "invited" | "removed";

// Mirrors backend/app/business/application/plan_limits.py's PLAN_LIMITS —
// duplicated here per this codebase's established per-layer convention,
// used only for the "X of Y team members used" display.
export const PLAN_LIMITS: Record<BusinessPlan, { maxTeamMembers: number; label: string }> = {
  free: { maxTeamMembers: 2, label: "Free" },
  starter: { maxTeamMembers: 5, label: "Starter" },
  pro: { maxTeamMembers: 20, label: "Pro" },
};

export interface BusinessResponse {
  id: string;
  owner_user_id: string;
  name: string;
  business_type: string | null;
  industry: string | null;
  country: string | null;
  currency: string;
  financial_year_start_month: number;
  gst_registered: boolean;
  business_size: string | null;
  number_of_branches: number;
  whatsapp_number: string | null;
  contact_email: string | null;
  onboarding_completed: boolean;
  status: BusinessStatus;
  plan: BusinessPlan;
  created_at: string;
}

export interface MyBusinessResponse {
  business: BusinessResponse;
  role: BusinessRole;
}

export interface RegisterBusinessRequest {
  name: string;
}

export interface CompleteOnboardingRequest {
  business_type?: string;
  industry?: string;
  country?: string;
  currency?: string;
  financial_year_start_month?: number;
  gst_registered?: boolean;
  business_size?: string;
  number_of_branches?: number;
  whatsapp_number?: string;
  contact_email?: string;
}

export interface ChangePlanRequest {
  plan: BusinessPlan;
}

export interface TeamMemberResponse {
  membership_id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: BusinessRole;
  status: MembershipStatus;
}

export interface InviteTeamMemberRequest {
  email: string;
  role: BusinessRole;
}

export interface UpdateTeamMemberRoleRequest {
  role: BusinessRole;
}
