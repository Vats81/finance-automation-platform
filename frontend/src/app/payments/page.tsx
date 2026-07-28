"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { listPayments } from "@/lib/api/payments";
import { useAuth } from "@/lib/auth/useAuth";
import { PaymentResponse, PaymentStatus } from "@/types/payment";

const STATUS_TONE: Record<PaymentStatus, "success" | "warning" | "danger" | "neutral"> = {
  scheduled: "warning",
  paid: "success",
  failed: "danger",
  cancelled: "neutral",
};

function PaymentsContent() {
  const { getAccessToken } = useAuth();
  const [payments, setPayments] = useState<PaymentResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken()
      .then((token) => listPayments(token))
      .then((page) => setPayments(page.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load payments"));
  }, [getAccessToken]);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">Payments</h1>
          <Card>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {!payments && !error ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : payments && payments.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                No payments scheduled yet — approved invoices appear here automatically.
              </p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2 pr-4">Amount</th>
                    <th className="py-2 pr-4">Scheduled date</th>
                    <th className="py-2 pr-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {payments?.map((payment) => (
                    <tr key={payment.id}>
                      <td className="py-3 pr-4">${payment.amount}</td>
                      <td className="py-3 pr-4">
                        {new Date(payment.scheduled_date).toLocaleDateString()}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge tone={STATUS_TONE[payment.status]}>{payment.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function PaymentsPage() {
  return (
    <AuthGuard>
      <PaymentsContent />
    </AuthGuard>
  );
}
