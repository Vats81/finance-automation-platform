"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { changeFirmStaffRole, inviteFirmStaff, listFirmStaff, removeFirmStaff } from "@/lib/api/firms";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ASSIGNABLE_FIRM_ROLES, FirmRole, FirmStaffResponse } from "@/types/firm";

const ROLE_HELP: Record<FirmRole, string> = {
  owner: "Everything. Created the firm; cannot be changed or removed.",
  admin: "Manages staff and clients. Works in client businesses as an admin.",
  accountant: "Records and edits data in client businesses, imports and exports.",
  viewer: "Looks only: no editing, importing or exporting.",
};

export default function FirmStaffPage() {
  const { getAccessToken, user } = useLocalAuth();
  const { currentFirm } = useCurrentBusiness();
  const [staff, setStaff] = useState<FirmStaffResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<FirmRole>("accountant");
  const [isInviting, setIsInviting] = useState(false);

  const canManage = currentFirm?.my_role === "owner" || currentFirm?.my_role === "admin";

  const load = useCallback(() => {
    if (!currentFirm) return;
    setLoadError(null);
    listFirmStaff(getAccessToken(), currentFirm.id)
      .then(setStaff)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [currentFirm, getAccessToken]);

  useEffect(() => {
    setStaff(null);
    load();
  }, [load]);

  async function handleInvite(event: FormEvent) {
    event.preventDefault();
    if (!currentFirm) return;
    setIsInviting(true);
    setActionError(null);
    try {
      await inviteFirmStaff(getAccessToken(), currentFirm.id, { email, role });
      setEmail("");
      load();
    } catch (err) {
      setActionError(errorMessage(err, "The invitation couldn't be saved."));
    } finally {
      setIsInviting(false);
    }
  }

  async function handleRole(member: FirmStaffResponse, newRole: FirmRole) {
    if (!currentFirm) return;
    setActionError(null);
    try {
      await changeFirmStaffRole(getAccessToken(), currentFirm.id, member.membership_id, newRole);
      load();
    } catch (err) {
      setActionError(errorMessage(err, "The role couldn't be changed."));
    }
  }

  async function handleRemove(member: FirmStaffResponse) {
    if (!currentFirm) return;
    if (!window.confirm(`Remove ${member.display_name}? They lose access to the firm and all its clients straight away.`)) {
      return;
    }
    setActionError(null);
    try {
      await removeFirmStaff(getAccessToken(), currentFirm.id, member.membership_id);
      load();
    } catch (err) {
      setActionError(errorMessage(err, "The person couldn't be removed."));
    }
  }

  if (!currentFirm) {
    return <p className="text-sm text-slate-500">You are not part of an accounting firm yet.</p>;
  }

  const active = staff?.filter((s) => s.status === "active") ?? [];

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Firm staff</h1>
      <p className="mb-6 text-sm text-slate-500">
        People who work at {currentFirm.name}. Their role here decides what they can do in every client
        business.
      </p>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      {canManage && (
        <Card className="mb-6">
          <form onSubmit={handleInvite} className="grid gap-3 sm:grid-cols-[1fr_12rem_auto] sm:items-end">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Add a colleague by email</span>
              <Input
                required
                type="email"
                placeholder="They must already have an account"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Role</span>
              <Select value={role} onChange={(e) => setRole(e.target.value as FirmRole)}>
                {ASSIGNABLE_FIRM_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </label>
            <Button type="submit" disabled={isInviting}>
              {isInviting ? "Adding…" : "Add"}
            </Button>
          </form>
          <p className="mt-2 text-xs text-slate-500">{ROLE_HELP[role]}</p>
        </Card>
      )}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={load} />
        ) : !staff ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 pr-4">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {active.map((member) => {
                const isOwner = member.role === "owner";
                const isSelf = member.user_id === user?.id;
                return (
                  <tr key={member.membership_id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-4 font-medium">{member.display_name}</td>
                    <td className="py-2 pr-4 text-slate-600">{member.email}</td>
                    <td className="py-2 pr-4">
                      {canManage && !isOwner && !isSelf ? (
                        <Select
                          aria-label={`Role for ${member.display_name}`}
                          value={member.role}
                          onChange={(e) => handleRole(member, e.target.value as FirmRole)}
                          className="max-w-[10rem]"
                        >
                          {ASSIGNABLE_FIRM_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        <Badge tone={isOwner ? "success" : "neutral"}>{member.role}</Badge>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      {canManage && !isOwner && (
                        <Button variant="ghost" onClick={() => handleRemove(member)}>
                          Remove
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
