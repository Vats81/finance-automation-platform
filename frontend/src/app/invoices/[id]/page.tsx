"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { ApproveRejectDialog } from "@/components/approvals/ApproveRejectDialog";
import { ApprovalTimeline } from "@/components/approvals/ApprovalTimeline";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { approveStep, getWorkflowForInvoice, rejectStep } from "@/lib/api/approvals";
import { fetchMe } from "@/lib/api/identity";
import { getInvoice } from "@/lib/api/invoices";
import { useAuth } from "@/lib/auth/useAuth";
import { ApprovalWorkflowResponse } from "@/types/approval";
import { InvoiceResponse, InvoiceStatus } from "@/types/invoice";
import { UserResponse } from "@/types/user";

const STATUS_TONE: Record<InvoiceStatus, "success" | "warning" | "danger" | "neutral"> = {
  submitted: "neutral",
  matched: "success",
  match_exception: "danger",
  pending_approval: "warning",
  approved: "success",
  rejected: "danger",
};

const IN_FLIGHT_STATUSES: InvoiceStatus[] = ["submitted"];

function InvoiceDetailContent() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useAuth();
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);
  const [workflow, setWorkflow] = useState<ApprovalWorkflowResponse | null>(null);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isActingOnStep, setIsActingOnStep] = useState(false);

  const load = useCallback(async () => {
    const token = await getAccessToken();
    const [data, me] = await Promise.all([getInvoice(token, id), fetchMe(token)]);
    setInvoice(data);
    setCurrentUser(me);

    if (data.status === "pending_approval" || data.status === "approved" || data.status === "rejected") {
      const wf = await getWorkflowForInvoice(token, id).catch(() => null);
      setWorkflow(wf);
    }
  }, [getAccessToken, id]);

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load invoice"));
  }, [load]);

  async function handleApprove() {
    if (!workflow) return;
    const step = workflow.steps.find((s) => s.status === "pending");
    if (!step) return;
    setIsActingOnStep(true);
    setError(null);
    try {
      const token = await getAccessToken();
      await approveStep(token, workflow.id, step.step_number);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve");
    } finally {
      setIsActingOnStep(false);
    }
  }

  async function handleReject(reason: string) {
    if (!workflow) return;
    const step = workflow.steps.find((s) => s.status === "pending");
    if (!step) return;
    setIsActingOnStep(true);
    setError(null);
    try {
      const token = await getAccessToken();
      await rejectStep(token, workflow.id, step.step_number, reason);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject");
    } finally {
      setIsActingOnStep(false);
    }
  }

  // Document processing + 2-way matching run asynchronously on the Celery
  // worker after submission — poll briefly while status is still SUBMITTED
  // so the UI reflects the match result without a manual refresh.
  useEffect(() => {
    if (!invoice || !IN_FLIGHT_STATUSES.includes(invoice.status)) return;
    const interval = setInterval(() => {
      load().catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, [invoice, load]);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
          {!invoice ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <>
              <div className="mb-6 flex items-center gap-3">
                <h1 className="text-2xl font-semibold">{invoice.invoice_number}</h1>
                <Badge tone={STATUS_TONE[invoice.status]}>{invoice.status.replace("_", " ")}</Badge>
                {IN_FLIGHT_STATUSES.includes(invoice.status) && <Spinner />}
              </div>

              {invoice.match_discrepancies.length > 0 && (
                <Card className="mb-6 border-red-200 bg-red-50">
                  <h2 className="mb-2 text-sm font-semibold text-red-700">Match exceptions</h2>
                  <ul className="list-inside list-disc space-y-1 text-sm text-red-700">
                    {invoice.match_discrepancies.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </Card>
              )}

              {workflow && (
                <Card className="mb-6">
                  <h2 className="mb-3 text-sm font-semibold text-slate-500">Approval workflow</h2>
                  <ApprovalTimeline steps={workflow.steps} />
                  {workflow.status === "in_progress" &&
                    currentUser &&
                    workflow.steps.find((s) => s.status === "pending")?.required_role ===
                      currentUser.role && (
                      <div className="mt-4">
                        <ApproveRejectDialog
                          onApprove={handleApprove}
                          onReject={handleReject}
                          isSubmitting={isActingOnStep}
                        />
                      </div>
                    )}
                </Card>
              )}

              <Card>
                <h2 className="mb-3 text-sm font-semibold text-slate-500">Line items</h2>
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="py-2 pr-4">#</th>
                      <th className="py-2 pr-4">Description</th>
                      <th className="py-2 pr-4">Qty</th>
                      <th className="py-2 pr-4">Unit price</th>
                      <th className="py-2 pr-4">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {invoice.line_items.map((item) => (
                      <tr key={item.line_number}>
                        <td className="py-2 pr-4">{item.line_number}</td>
                        <td className="py-2 pr-4">{item.description}</td>
                        <td className="py-2 pr-4">{item.quantity}</td>
                        <td className="py-2 pr-4">${item.unit_price}</td>
                        <td className="py-2 pr-4">${item.line_total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-4 text-right text-sm font-semibold">Total: ${invoice.total_amount}</p>
              </Card>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default function InvoiceDetailPage() {
  return (
    <AuthGuard>
      <InvoiceDetailContent />
    </AuthGuard>
  );
}
