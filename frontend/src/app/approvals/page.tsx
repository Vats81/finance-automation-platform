"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { ApproveRejectDialog } from "@/components/approvals/ApproveRejectDialog";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { approveStep, listPendingApprovals, rejectStep } from "@/lib/api/approvals";
import { useAuth } from "@/lib/auth/useAuth";
import { ApprovalWorkflowResponse } from "@/types/approval";

function ApprovalsContent() {
  const { getAccessToken } = useAuth();
  const [workflows, setWorkflows] = useState<ApprovalWorkflowResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actingWorkflowId, setActingWorkflowId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = await getAccessToken();
    const page = await listPendingApprovals(token);
    setWorkflows(page.items);
  }, [getAccessToken]);

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load approvals"));
  }, [load]);

  async function handleApprove(workflow: ApprovalWorkflowResponse) {
    const step = workflow.steps.find((s) => s.status === "pending");
    if (!step) return;
    setActingWorkflowId(workflow.id);
    setError(null);
    try {
      const token = await getAccessToken();
      await approveStep(token, workflow.id, step.step_number);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve");
    } finally {
      setActingWorkflowId(null);
    }
  }

  async function handleReject(workflow: ApprovalWorkflowResponse, reason: string) {
    const step = workflow.steps.find((s) => s.status === "pending");
    if (!step) return;
    setActingWorkflowId(workflow.id);
    setError(null);
    try {
      const token = await getAccessToken();
      await rejectStep(token, workflow.id, step.step_number, reason);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject");
    } finally {
      setActingWorkflowId(null);
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">My pending approvals</h1>
          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          {!workflows ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : workflows.length === 0 ? (
            <Card>
              <p className="py-8 text-center text-sm text-slate-500">Nothing pending your approval.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {workflows.map((workflow) => {
                const step = workflow.steps.find((s) => s.status === "pending");
                return (
                  <Card key={workflow.id}>
                    <div className="mb-3 flex items-center justify-between">
                      <div>
                        <Link
                          href={`/invoices/${workflow.invoice_id}`}
                          className="font-medium text-brand-700 hover:underline"
                        >
                          Invoice {workflow.invoice_id.slice(0, 8)}…
                        </Link>
                        {step && (
                          <Badge tone="warning">
                            Step {step.step_number} of {workflow.steps.length}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <ApproveRejectDialog
                      onApprove={() => handleApprove(workflow)}
                      onReject={(reason) => handleReject(workflow, reason)}
                      isSubmitting={actingWorkflowId === workflow.id}
                    />
                  </Card>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default function ApprovalsPage() {
  return (
    <AuthGuard>
      <ApprovalsContent />
    </AuthGuard>
  );
}
