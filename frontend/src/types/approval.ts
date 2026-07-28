export type ApprovalStepStatus = "pending" | "approved" | "rejected";
export type ApprovalWorkflowStatus = "in_progress" | "approved" | "rejected";
export type Role = "ap_clerk" | "approver" | "finance_admin";

export interface ApprovalStepResponse {
  step_number: number;
  required_role: Role;
  status: ApprovalStepStatus;
  approver_user_id: string | null;
  decided_at: string | null;
  comment: string | null;
}

export interface ApprovalWorkflowResponse {
  id: string;
  invoice_id: string;
  status: ApprovalWorkflowStatus;
  steps: ApprovalStepResponse[];
  created_at: string;
}

export interface PagedApprovalWorkflowsResponse {
  items: ApprovalWorkflowResponse[];
  total: number;
  offset: number;
  limit: number;
}
