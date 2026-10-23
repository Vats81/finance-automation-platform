export type BusinessRole = "owner" | "admin" | "accountant" | "viewer";
export type BusinessStatus = "active" | "suspended";
export type BusinessPlan = "free" | "starter" | "pro";
export type MembershipStatus = "active" | "invited" | "removed";
export type BusinessKind = "business" | "personal";

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
  kind?: BusinessKind;
  firm_id?: string | null;
  created_at: string;
}

export interface MyBusinessResponse {
  business: BusinessResponse;
  role: BusinessRole;
  // True when this business is reached through an accounting firm, not the business's own team.
  via_firm?: boolean;
  firm_name?: string | null;
}

export interface RegisterBusinessRequest {
  name: string;
  kind?: BusinessKind;
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
