import { BusinessPlan } from "@/types/business";

export type AdminBusinessStatus = "active" | "suspended";

export interface BusinessOverview {
  id: string;
  name: string;
  plan: BusinessPlan;
  status: AdminBusinessStatus;
  member_count: number;
  owner_email: string;
  created_at: string;
}

export interface BusinessesOverviewResponse {
  items: BusinessOverview[];
  total: number;
  offset: number;
  limit: number;
}

export interface UserOverview {
  id: string;
  email: string;
  display_name: string;
  is_email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface UsersOverviewResponse {
  items: UserOverview[];
  total: number;
  offset: number;
  limit: number;
}

export interface PlatformStats {
  total_businesses: number;
  total_users: number;
  businesses_by_plan: Record<string, number>;
  verified_users: number;
  unverified_users: number;
}
