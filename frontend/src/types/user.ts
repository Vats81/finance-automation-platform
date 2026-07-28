export type Role = "ap_clerk" | "approver" | "finance_admin";

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}
