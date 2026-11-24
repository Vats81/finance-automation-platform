export type BusinessRole = "owner" | "admin" | "accountant" | "viewer";
export type BusinessStatus = "active" | "suspended";
export type BusinessPlan = "free" | "starter" | "pro";
export type MembershipStatus = "active" | "invited" | "removed";
export type BusinessKind = "business" | "personal";

// Mirrors backend/app/business/application/plan_limits.py's PLAN_LIMITS —
// duplicated here per this codebase's established per-layer convention,
// used only for the "X of Y team members used" display.
export const PLAN_LIMITS: Record<BusinessPlan, { maxTeamMembers: number; label: string }> = {
  free: { maxTeamMembers: 10, label: "Free" }, // raised for the private beta
  starter: { maxTeamMembers: 10, label: "Starter" },
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
  gstin?: string | null;
  address_line?: string | null;
  city?: string | null;
  state_code?: string | null;
  pincode?: string | null;
  phone?: string | null;
  upi_id?: string | null;
  summary_frequency?: SummaryFrequency;
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
  gstin?: string;
  address_line?: string;
  city?: string;
  state_code?: string;
  pincode?: string;
  phone?: string;
  upi_id?: string;
  summary_frequency?: SummaryFrequency;
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

/** How often the WhatsApp summary is sent on its own. */
export type SummaryFrequency = "off" | "daily" | "weekly";
