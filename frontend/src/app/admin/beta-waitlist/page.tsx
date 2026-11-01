"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import {
  deleteWaitlistEntry,
  getInvitationDraft,
  InvitationDraft,
  listWaitlist,
  sendInvitationEmail,
  updateWaitlistEntry,
  WaitlistEntry,
  WaitlistStatus,
} from "@/lib/api/betaWaitlist";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";

const STATUS_LABEL: Record<WaitlistStatus, string> = {
  interested: "Interested",
  qualified: "Qualified",
  waiting_for_checks: "Waiting for checks",
  invited: "Invited",
  onboarded: "Onboarded",
  paused: "Paused",
};

// Mirrors backend/app/beta_waitlist/domain/status.py; the server enforces it.
const NEXT: Record<WaitlistStatus, WaitlistStatus[]> = {
  interested: ["qualified", "paused"],
  qualified: ["waiting_for_checks", "invited", "paused"],
  waiting_for_checks: ["qualified", "invited", "paused"],
  invited: ["onboarded", "qualified", "paused"],
  onboarded: ["paused"],
  paused: ["interested", "qualified"],
};

const TONE: Record<WaitlistStatus, "neutral" | "success" | "warning" | "danger"> = {
  interested: "neutral",
  qualified: "success",
  waiting_for_checks: "warning",
  invited: "success",
  onboarded: "success",
  paused: "danger",
};

export default function AdminBetaWaitlistPage() {
  const { getAccessToken } = useLocalAuth();
  const [entries, setEntries] = useState<WaitlistEntry[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  // The invitation being composed: the draft from the server, which the owner edits before sending.
  const [composing, setComposing] = useState<{ entry: WaitlistEntry; draft: InvitationDraft } | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sentNotice, setSentNotice] = useState<string | null>(null);

  useEffect(() => {
    setEntries(null);
    setLoadError(null);
    listWaitlist(getAccessToken())
      .then(setEntries)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [getAccessToken, retryToken]);

  function replace(updated: WaitlistEntry) {
    setEntries((current) => current?.map((e) => (e.id === updated.id ? updated : e)) ?? current);
  }

  async function move(entry: WaitlistEntry, status: WaitlistStatus) {
    setActionError(null);
    try {
      replace(await updateWaitlistEntry(getAccessToken(), entry.id, { status }));
    } catch (err) {
      setActionError(errorMessage(err, "That change couldn't be saved."));
    }
  }

  async function openInvitation(entry: WaitlistEntry) {
    setActionError(null);
    setSentNotice(null);
    try {
      const draft = await getInvitationDraft(getAccessToken(), entry.id);
      setSubject(draft.subject);
      setBody(draft.body);
      setComposing({ entry, draft });
    } catch (err) {
      setActionError(errorMessage(err, "The invitation draft couldn't be loaded."));
    }
  }

  async function sendInvitation() {
    if (!composing) return;
    const { entry, draft } = composing;
    const again = draft.already_sent_at !== null;
    if (
      !window.confirm(
        `${again ? "This address has already been sent an invitation. Send it AGAIN to" : "Send this email to"} ${
          entry.work_email
        }?\n\nIt goes out immediately and cannot be recalled.`
      )
    ) {
      return;
    }
    setIsSending(true);
    setActionError(null);
    try {
      replace(await sendInvitationEmail(getAccessToken(), entry.id, { subject, body, resend: again }));
      setSentNotice(`Invitation sent to ${entry.work_email}.`);
      setComposing(null);
    } catch (err) {
      setActionError(errorMessage(err, "The invitation couldn't be sent."));
    } finally {
      setIsSending(false);
    }
  }

  async function editNotes(entry: WaitlistEntry) {
    const notes = window.prompt("Notes (visible to admins only)", entry.notes ?? "");
    if (notes === null) return;
    setActionError(null);
    try {
      replace(await updateWaitlistEntry(getAccessToken(), entry.id, { notes }));
    } catch (err) {
      setActionError(errorMessage(err, "Notes couldn't be saved."));
    }
  }

  async function remove(entry: WaitlistEntry) {
    if (!window.confirm(`Delete ${entry.work_email} from the waitlist? This cannot be undone.`)) return;
    setActionError(null);
    try {
      await deleteWaitlistEntry(getAccessToken(), entry.id);
      setEntries((current) => current?.filter((e) => e.id !== entry.id) ?? current);
    } catch (err) {
      setActionError(errorMessage(err, "The entry couldn't be deleted."));
    }
  }

  const counts = (Object.keys(STATUS_LABEL) as WaitlistStatus[]).map((status) => ({
    status,
    count: entries?.filter((e) => e.status === status).length ?? 0,
  }));

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Beta waitlist</h1>
      <p className="mb-4 text-sm text-slate-500">
        Interest in the private beta. An entry grants no access and creates no account; moving someone to
        &ldquo;Invited&rdquo; here does not send anything; it only lets that email address sign up. When
        you are ready, use &ldquo;Send invitation email&rdquo; on an invited row: you can edit the message
        and nothing goes out until you confirm.
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        {counts.map(({ status, count }) => (
          <Badge key={status} tone={TONE[status]}>
            {STATUS_LABEL[status]}: {count}
          </Badge>
        ))}
      </div>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}
      {sentNotice && <p className="mb-3 text-sm text-emerald-700">{sentNotice}</p>}

      {composing && (
        <Card className="mb-4 border-brand-500">
          <h2 className="mb-1 text-lg font-semibold">Invitation to {composing.entry.name}</h2>
          <p className="mb-3 text-sm text-slate-500">
            To: <span className="font-medium text-slate-700">{composing.entry.work_email}</span>. Replies go to
            the support address. Edit anything below; it is sent exactly as written.
            {composing.draft.already_sent_at && (
              <span className="ml-1 font-medium text-amber-700">
                An invitation was already sent on {new Date(composing.draft.already_sent_at).toLocaleString()}.
              </span>
            )}
          </p>
          <label className="mb-1 block text-sm font-medium" htmlFor="invite-subject">
            Subject
          </label>
          <input
            id="invite-subject"
            value={subject}
            maxLength={200}
            onChange={(e) => setSubject(e.target.value)}
            className="mb-3 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <label className="mb-1 block text-sm font-medium" htmlFor="invite-body">
            Message
          </label>
          <textarea
            id="invite-body"
            value={body}
            maxLength={5000}
            rows={16}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
          />
          <div className="mt-3 flex gap-3">
            <Button onClick={sendInvitation} disabled={isSending || !subject.trim() || !body.trim()}>
              {isSending ? "Sending…" : composing.draft.already_sent_at ? "Send again" : "Send invitation"}
            </Button>
            <Button variant="secondary" onClick={() => setComposing(null)} disabled={isSending}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={() => setRetryToken((n) => n + 1)} />
        ) : !entries ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-slate-500">No one has registered interest yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {entries.map((entry) => (
              <li key={entry.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-medium text-slate-900">
                    {entry.name}{" "}
                    <a href={`mailto:${entry.work_email}`} className="font-normal text-brand-600 underline">
                      {entry.work_email}
                    </a>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Badge tone={TONE[entry.status]}>{STATUS_LABEL[entry.status]}</Badge>
                    {entry.invitation_sent_at && (
                      <Badge tone="success">
                        Invitation sent {new Date(entry.invitation_sent_at).toLocaleDateString("en-US")}
                      </Badge>
                    )}
                    {new Date(entry.created_at).toLocaleDateString("en-US")}
                  </div>
                </div>
                <dl className="mt-1 grid gap-x-6 gap-y-1 text-sm text-slate-600 sm:grid-cols-2">
                  {entry.business_name && <div>Business: {entry.business_name}</div>}
                  {entry.business_type && <div>Type: {entry.business_type}</div>}
                  {entry.bookkeeping_method && <div>Books today: {entry.bookkeeping_method}</div>}
                  <div>Weekly feedback: {entry.weekly_feedback_ok ? "yes" : "not stated"}</div>
                </dl>
                {entry.reporting_problem && (
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{entry.reporting_problem}</p>
                )}
                {entry.notes && <p className="mt-1 text-sm italic text-slate-500">Notes: {entry.notes}</p>}
                <div className="mt-2 flex flex-wrap gap-2">
                  {NEXT[entry.status].map((next) => (
                    <Button key={next} variant="secondary" onClick={() => move(entry, next)}>
                      Move to {STATUS_LABEL[next]}
                    </Button>
                  ))}
                  {entry.status === "invited" && (
                    <Button onClick={() => openInvitation(entry)}>
                      {entry.invitation_sent_at ? "Send invitation again" : "Send invitation email"}
                    </Button>
                  )}
                  <Button variant="secondary" onClick={() => editNotes(entry)}>
                    Notes
                  </Button>
                  <Button variant="danger" onClick={() => remove(entry)}>
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
