"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

export function ApproveRejectDialog({
  onApprove,
  onReject,
  isSubmitting,
}: {
  onApprove: () => void;
  onReject: (reason: string) => void;
  isSubmitting: boolean;
}) {
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [reason, setReason] = useState("");

  if (showRejectForm) {
    return (
      <div className="space-y-2">
        <textarea
          required
          placeholder="Reason for rejection"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
        />
        <div className="flex gap-2">
          <Button
            variant="danger"
            disabled={isSubmitting || !reason.trim()}
            onClick={() => onReject(reason)}
          >
            {isSubmitting ? "Rejecting…" : "Confirm rejection"}
          </Button>
          <Button variant="ghost" onClick={() => setShowRejectForm(false)} disabled={isSubmitting}>
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <Button onClick={onApprove} disabled={isSubmitting}>
        {isSubmitting ? "Approving…" : "Approve"}
      </Button>
      <Button variant="danger" onClick={() => setShowRejectForm(true)} disabled={isSubmitting}>
        Reject
      </Button>
    </div>
  );
}
