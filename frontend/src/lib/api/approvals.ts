import { apiFetch } from "@/lib/api/client";
import { ApprovalWorkflowResponse, PagedApprovalWorkflowsResponse } from "@/types/approval";

export function listPendingApprovals(token: string | null): Promise<PagedApprovalWorkflowsResponse> {
  return apiFetch<PagedApprovalWorkflowsResponse>("/approvals/pending", token);
}

export function getWorkflowForInvoice(
  token: string | null,
  invoiceId: string
): Promise<ApprovalWorkflowResponse> {
  return apiFetch<ApprovalWorkflowResponse>(`/approvals/invoice/${invoiceId}`, token);
}

export function approveStep(
  token: string | null,
  workflowId: string,
  stepNumber: number
): Promise<ApprovalWorkflowResponse> {
  return apiFetch<ApprovalWorkflowResponse>(`/approvals/${workflowId}/steps/${stepNumber}/approve`, token, {
    method: "POST",
  });
}

export function rejectStep(
  token: string | null,
  workflowId: string,
  stepNumber: number,
  reason: string
): Promise<ApprovalWorkflowResponse> {
  return apiFetch<ApprovalWorkflowResponse>(`/approvals/${workflowId}/steps/${stepNumber}/reject`, token, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
